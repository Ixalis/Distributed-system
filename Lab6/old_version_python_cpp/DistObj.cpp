// DistObj.h
//#ifndef DIST_OBJ_H
//#define DIST_OBJ_H

#include <mpi.h>
#include <vector>
#include <iostream>
#include <mutex>
#include <condition_variable>

template <class T>
class DistObj {
private:
    T _obj;
    int rank;
    int world_size;
    std::vector<bool> read_tokens;
    bool write_token;
    std::mutex mutex;
    std::condition_variable cv;

    // Internal message tags
    enum MessageTag {
        TOKEN_REQUEST = 0,
        TOKEN_RESPONSE = 1,
        NEW_PROCESS = 2,
        VALUE_UPDATE = 3
    };

    void initMPI();
    bool hasAllTokens();
    void requestTokens();
    void handleTokenRequests();
    void receiveTokens();
    void broadcastNewProcess();

public:
    DistObj(T& val);
    DistObj();
    T read();
    void write(T val);
    ~DistObj() {}
};

// Template implementation
template <class T>
void DistObj<T>::initMPI() {
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);
    read_tokens.resize(world_size, false);
    read_tokens[rank] = true;
    write_token = (rank == 0);
}

template <class T>
bool DistObj<T>::hasAllTokens() {
    if (!write_token) return false;
    for (bool token : read_tokens) {
        if (!token) return false;
    }
    return true;
}

template <class T>
void DistObj<T>::requestTokens() {
    if (!write_token) {
        for (int i = 0; i < world_size; i++) {
            if (i != rank) {
                MPI_Send(&rank, 1, MPI_INT, i, TOKEN_REQUEST, MPI_COMM_WORLD);
            }
        }
    }

    for (int i = 0; i < world_size; i++) {
        if (i != rank && !read_tokens[i]) {
            MPI_Send(&rank, 1, MPI_INT, i, TOKEN_REQUEST, MPI_COMM_WORLD);
        }
    }
}

template <class T>
void DistObj<T>::handleTokenRequests() {
    MPI_Status status;
    int flag;
    int requesting_rank;

    MPI_Iprobe(MPI_ANY_SOURCE, TOKEN_REQUEST, MPI_COMM_WORLD, &flag, &status);
    
    if (flag) {
        MPI_Recv(&requesting_rank, 1, MPI_INT, status.MPI_SOURCE, TOKEN_REQUEST, 
                MPI_COMM_WORLD, &status);

        if (write_token) {
            write_token = false;
            MPI_Send(&rank, 1, MPI_INT, requesting_rank, TOKEN_RESPONSE, MPI_COMM_WORLD);
        }

        if (read_tokens[rank]) {
            read_tokens[rank] = false;
            MPI_Send(&rank, 1, MPI_INT, requesting_rank, TOKEN_RESPONSE, MPI_COMM_WORLD);
        }
    }
}

template <class T>
void DistObj<T>::receiveTokens() {
    MPI_Status status;
    int flag;
    int sender_rank;

    MPI_Iprobe(MPI_ANY_SOURCE, TOKEN_RESPONSE, MPI_COMM_WORLD, &flag, &status);
    
    if (flag) {
        MPI_Recv(&sender_rank, 1, MPI_INT, status.MPI_SOURCE, TOKEN_RESPONSE, 
                MPI_COMM_WORLD, &status);
        read_tokens[sender_rank] = true;
        write_token = true;
    }
}

template <class T>
void DistObj<T>::broadcastNewProcess() {
    for (int i = 0; i < world_size; i++) {
        if (i != rank) {
            MPI_Send(&rank, 1, MPI_INT, i, NEW_PROCESS, MPI_COMM_WORLD);
        }
    }
}

template <class T>
DistObj<T>::DistObj(T& val) : _obj(val) {
    initMPI();
    
    if (rank == 0) {
        write(_obj);
    } else {
        MPI_Status status;
        MPI_Recv(&_obj, sizeof(T), MPI_BYTE, 0, VALUE_UPDATE, MPI_COMM_WORLD, &status);
    }

    broadcastNewProcess();
}

template <class T>
DistObj<T>::DistObj() : _obj() {
    initMPI();
    
    if (rank == 0) {
        write(_obj);
    } else {
        MPI_Status status;
        MPI_Recv(&_obj, sizeof(T), MPI_BYTE, 0, VALUE_UPDATE, MPI_COMM_WORLD, &status);
    }

    broadcastNewProcess();
}

template <class T>
T DistObj<T>::read() {
    std::unique_lock<std::mutex> lock(mutex);
    
    if (!read_tokens[rank]) {
        requestTokens();
        while (!read_tokens[rank]) {
            handleTokenRequests();
            receiveTokens();
        }
    }
    
    std::cout << "Process " << rank << " reading value: " << _obj << std::endl;
    return _obj;
}

template <class T>
void DistObj<T>::write(T val) {
    std::unique_lock<std::mutex> lock(mutex);
    
    if (!hasAllTokens()) {
        requestTokens();
        while (!hasAllTokens()) {
            handleTokenRequests();
            receiveTokens();
        }
    }
    
    _obj = val;
    std::cout << "Process " << rank << " writing value: " << _obj << std::endl;
    
    for (int i = 0; i < world_size; i++) {
        if (i != rank) {
            MPI_Send(&_obj, sizeof(T), MPI_BYTE, i, VALUE_UPDATE, MPI_COMM_WORLD);
        }
    }
}

//#endif // DIST_OBJ_H