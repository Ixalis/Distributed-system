import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.rmi.server.UnicastRemoteObject;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

public class DistObj extends UnicastRemoteObject implements DistObjInterface {
    private Object value;
    private final String nodeId;
    private final Map<String, DistObjInterface> peers;
    private final Set<String> readTokenHolders;
    private String writeTokenHolder;
    private final ReentrantLock lock;
    private static final int RMI_PORT = 1099;

    public DistObj(Object initialValue, String nodeId) throws RemoteException {
        this.value = initialValue;
        this.nodeId = nodeId;
        this.peers = new ConcurrentHashMap<>();
        this.readTokenHolders = Collections.synchronizedSet(new HashSet<>());
        this.writeTokenHolder = nodeId; // Initially, creator holds write token
        this.lock = new ReentrantLock();

        // Register with RMI registry
        try {
            Registry registry = LocateRegistry.createRegistry(RMI_PORT);
            registry.rebind(nodeId, this);
        } catch (RemoteException e) {
            Registry registry = LocateRegistry.getRegistry(RMI_PORT);
            registry.rebind(nodeId, this);
        }
    }

    public DistObj(String nodeId) throws RemoteException {
        this(null, nodeId);
        // Join existing network if other nodes exist
        try {
            Registry registry = LocateRegistry.getRegistry(RMI_PORT);
            String[] nodes = registry.list();
            if (nodes.length > 0) {
                for (String node : nodes) {
                    if (!node.equals(nodeId)) {
                        DistObjInterface peer = (DistObjInterface) registry.lookup(node);
                        peer.joinNetwork(nodeId, this);
                        break;
                    }
                }
            }
        } catch (Exception e) {
            throw new RemoteException("Failed to join network", e);
        }
    }

    @Override
    public void joinNetwork(String clientId, DistObjInterface client) throws RemoteException {
        lock.lock();
        try {
            peers.put(clientId, client);
            // Share current value and peers with new client
            client.updateValue(value);
            for (Map.Entry<String, DistObjInterface> entry : peers.entrySet()) {
                if (!entry.getKey().equals(clientId)) {
                    client.joinNetwork(entry.getKey(), entry.getValue());
                }
            }
            // Notify all peers about the new client
            for (DistObjInterface peer : peers.values()) {
                if (!peer.equals(client)) {
                    peer.joinNetwork(clientId, client);
                }
            }
        } finally {
            lock.unlock();
        }
    }

    public Object read() throws RemoteException {
        requestReadToken(nodeId);
        Object result = value;
        releaseReadToken(nodeId);
        return result;
    }

    public void write(Object newValue) throws RemoteException {
        requestWriteToken(nodeId);
        try {
            this.value = newValue;
            // Propagate update to all peers
            for (DistObjInterface peer : peers.values()) {
                peer.updateValue(newValue);
            }
        } finally {
            releaseWriteToken(nodeId);
        }
    }

    @Override
    public void requestReadToken(String requesterId) throws RemoteException {
        lock.lock();
        try {
            while (writeTokenHolder != null && !writeTokenHolder.equals(requesterId)) {
                // Wait for write token to be released
                lock.unlock();
                Thread.sleep(100);
                lock.lock();
            }
            readTokenHolders.add(requesterId);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RemoteException("Interrupted while waiting for read token", e);
        } finally {
            lock.unlock();
        }
    }

    @Override
    public void releaseReadToken(String releaserId) throws RemoteException {
        lock.lock();
        try {
            readTokenHolders.remove(releaserId);
        } finally {
            lock.unlock();
        }
    }

    @Override
    public void requestWriteToken(String requesterId) throws RemoteException {
        lock.lock();
        try {
            while (!readTokenHolders.isEmpty() || 
                   (writeTokenHolder != null && !writeTokenHolder.equals(requesterId))) {
                // Wait for all read tokens and write token to be released
                lock.unlock();
                Thread.sleep(100);
                lock.lock();
            }
            writeTokenHolder = requesterId;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RemoteException("Interrupted while waiting for write token", e);
        } finally {
            lock.unlock();
        }
    }

    @Override
    public void releaseWriteToken(String releaserId) throws RemoteException {
        lock.lock();
        try {
            if (writeTokenHolder.equals(releaserId)) {
                writeTokenHolder = null;
            }
        } finally {
            lock.unlock();
        }
    }

    @Override
    public void updateValue(Object newValue) throws RemoteException {
        lock.lock();
        try {
            this.value = newValue;
        } finally {
            lock.unlock();
        }
    }

    @Override
    public Object getCurrentValue() throws RemoteException {
        return value;
    }
}
