# Cihan Sebzeci
# Comp 117 Spring 2018
____________

## About

This project was completed for [Internet Scale Distributed Systems](http://www.cs.tufts.edu/comp/117/). It creates client and server code for an RPC system over TCP
for any C++ file meeting the IDL syntax specified [here](http://www.cs.tufts.edu/comp/150IDS/assts/rpc#typefunctionidl). The Makefile links the resulting .proxy.cpp file to the client and the server is linked the resulting .stub.cpp file resulting in a program that runs as an RPC completely transparent to the developer.

The pipeline begins with an IDL file which specifies all function signatures and user defined types such as structs or statically allocated arrays. From this, the rpcgenerate script uses the idl_to_json parser to create proxy and stub .cpp files based on the IDL file.

