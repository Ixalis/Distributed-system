// main.cpp
#include "DistObj.cpp"
#include <unistd.h> // For sleep

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    
    int initial_value = 42;
    DistObj<int> dist_int(initial_value);
    
    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    
    // Add some delay to ensure proper initialization
    sleep(1);
    
    if (rank == 0) {
        std::cout << "Process " << rank << " initializing write operation..." << std::endl;
        dist_int.write(100);
    }
    
    // Add small delay between write and read
    sleep(1);
    
    // All processes read
    int value = dist_int.read();
    std::cout << "Process " << rank << " final read value: " << value << std::endl;
    
    // Ensure all output is printed before finalizing
    MPI_Barrier(MPI_COMM_WORLD);
    sleep(1);
    
    MPI_Finalize();
    return 0;
}