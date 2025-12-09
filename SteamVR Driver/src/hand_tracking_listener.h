//============ Copyright (c) Valve Corporation, All rights reserved. ============
#pragma once

#include <thread>
#include <atomic>
#include <string>
#include <sstream>
#include <map>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#define SOCKET int
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket close
#endif

class MyControllerDeviceDriver;

//-----------------------------------------------------------------------------
// Purpose: Listens for hand tracking data from the Python script via socket
//-----------------------------------------------------------------------------
class HandTrackingListener
{
public:
	HandTrackingListener( MyControllerDeviceDriver *left_controller, MyControllerDeviceDriver *right_controller );
	~HandTrackingListener();

	bool Start( int port = 65432 );
	void Stop();

private:
	void ListenThread();
	void ProcessHandData( const std::string &data );
	std::map<std::string, std::string> ParseProtocolString( const std::string &data );

	MyControllerDeviceDriver *left_controller_;
	MyControllerDeviceDriver *right_controller_;

	std::atomic<bool> is_running_;
	std::thread listen_thread_;
	
	SOCKET server_socket_;
	SOCKET client_socket_;
	int port_;
};
