## About
It creates client and server code for an RPC system over TCP
for any C++ file meeting the IDL syntax specified [here](http://www.cs.tufts.edu/comp/150IDS/assts/rpc#typefunctionidl). The Makefile links the resulting .proxy.cpp file to the client and the server is linked the resulting .stub.cpp file resulting in a program that runs as an RPC completely transparent to the developer.
