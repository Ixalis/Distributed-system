// DistObjDemo.java
import java.rmi.RemoteException;
import java.util.concurrent.TimeUnit;

public class DistObjDemo {
    public static void main(String[] args) {
        if (args.length != 2) {
            System.out.println("Usage: java DistObjDemo <nodeId> <role>");
            System.out.println("role can be: initializer, reader, writer");
            return;
        }

        String nodeId = args[0];
        String role = args[1];

        try {
            DistObj node;
            
            if (role.equals("initializer")) {
                // First node initializes with value 0
                System.out.println("Starting initializer node: " + nodeId);
                node = new DistObj(0, nodeId);
                // Keep the process alive
                while (true) {
                    System.out.println(nodeId + " current value: " + node.getCurrentValue());
                    TimeUnit.SECONDS.sleep(2);
                }
            } else if (role.equals("reader")) {
                // Reader nodes join network and continuously read
                System.out.println("Starting reader node: " + nodeId);
                node = new DistObj(nodeId);
                while (true) {
                    try {
                        Integer value = (Integer) node.read();
                        System.out.println(nodeId + " read value: " + value);
                        TimeUnit.SECONDS.sleep(1);
                    } catch (RemoteException e) {
                        System.out.println(nodeId + " failed to read: " + e.getMessage());
                    }
                }
            } else if (role.equals("writer")) {
                // Writer node joins network and periodically writes incremented values
                System.out.println("Starting writer node: " + nodeId);
                node = new DistObj(nodeId);
                int writeValue = 0;
                while (true) {
                    try {
                        writeValue += 10;
                        System.out.println(nodeId + " attempting to write: " + writeValue);
                        node.write(writeValue);
                        System.out.println(nodeId + " successfully wrote: " + writeValue);
                        TimeUnit.SECONDS.sleep(5);
                    } catch (RemoteException e) {
                        System.out.println(nodeId + " failed to write: " + e.getMessage());
                    }
                }
            }
        } catch (Exception e) {
            System.out.println("Error in node " + nodeId + ": " + e.getMessage());
            e.printStackTrace();
        }
    }
}