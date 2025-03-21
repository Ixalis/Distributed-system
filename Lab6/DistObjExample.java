import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.rmi.NotBoundException;

public class DistObjExample {
    public static void main(String[] args) {
        try {
            // Create nodes with initial values (now using Object instead of generics)
            DistObj node1 = new DistObj(42, "node1");
            DistObj node2 = new DistObj(42, "node2");

            // Display the values to verify
            System.out.println("Node 1 initial value: " + node1.getCurrentValue());
            System.out.println("Node 2 initial value: " + node2.getCurrentValue());

            // Use RMI registry to lookup nodes
            Registry registry = LocateRegistry.getRegistry(1099);

            DistObjInterface node1Remote = null;
            DistObjInterface node2Remote = null;

            try {
                node1Remote = (DistObjInterface) registry.lookup("node1");
                node2Remote = (DistObjInterface) registry.lookup("node2");
            } catch (NotBoundException e) {
                System.out.println("Node not found in registry: " + e.getMessage());
                e.printStackTrace();
            }

            // Simulate a value update if the nodes were found
            if (node1Remote != null) {
                node1Remote.updateValue(100);  // Set value to 100
                System.out.println("Updated Node 1 value: " + node1Remote.getCurrentValue());
            }

            if (node2Remote != null) {
                node2Remote.updateValue(100);  // Set value to 100
                System.out.println("Updated Node 2 value: " + node2Remote.getCurrentValue());
            }

        } catch (RemoteException e) {
            e.printStackTrace();
        }
    }
}
