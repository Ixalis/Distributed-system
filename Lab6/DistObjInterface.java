import java.rmi.Remote;
import java.rmi.RemoteException;

public interface DistObjInterface extends Remote {
    void joinNetwork(String clientId, DistObjInterface client) throws RemoteException;
    void requestReadToken(String requesterId) throws RemoteException;
    void releaseReadToken(String releaserId) throws RemoteException;
    void requestWriteToken(String requesterId) throws RemoteException;
    void releaseWriteToken(String releaserId) throws RemoteException;
    void updateValue(Object newValue) throws RemoteException; // Use Object instead of T
    Object getCurrentValue() throws RemoteException; // Use Object instead of T
}

