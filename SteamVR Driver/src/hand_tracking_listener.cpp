//============ Copyright (c) Valve Corporation, All rights reserved. ============
#include "hand_tracking_listener.h"
#include "controller_device_driver.h"
#include "driverlog.h"

#include <cstring>

HandTrackingListener::HandTrackingListener( MyControllerDeviceDriver *left_controller, MyControllerDeviceDriver *right_controller )
	: left_controller_( left_controller )
	, right_controller_( right_controller )
	, is_running_( false )
	, server_socket_( INVALID_SOCKET )
	, client_socket_( INVALID_SOCKET )
	, port_( 65432 )
{
}

HandTrackingListener::~HandTrackingListener()
{
	Stop();
}

bool HandTrackingListener::Start( int port )
{
	port_ = port;

#ifdef _WIN32
	// Initialize Winsock
	WSADATA wsa_data;
	if ( WSAStartup( MAKEWORD( 2, 2 ), &wsa_data ) != 0 )
	{
		DriverLog( "HandTrackingListener: WSAStartup failed" );
		return false;
	}
#endif

	// Create socket
	server_socket_ = socket( AF_INET, SOCK_STREAM, 0 );
	if ( server_socket_ == INVALID_SOCKET )
	{
		DriverLog( "HandTrackingListener: Failed to create socket" );
#ifdef _WIN32
		WSACleanup();
#endif
		return false;
	}

	// Set socket options to allow reuse
	int opt = 1;
#ifdef _WIN32
	setsockopt( server_socket_, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof( opt ) );
#else
	setsockopt( server_socket_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof( opt ) );
#endif

	// Bind socket
	struct sockaddr_in server_addr;
	memset( &server_addr, 0, sizeof( server_addr ) );
	server_addr.sin_family = AF_INET;
	server_addr.sin_addr.s_addr = inet_addr( "127.0.0.1" );
	server_addr.sin_port = htons( port_ );

	if ( bind( server_socket_, (struct sockaddr *)&server_addr, sizeof( server_addr ) ) == SOCKET_ERROR )
	{
		DriverLog( "HandTrackingListener: Failed to bind socket to port %d", port_ );
		closesocket( server_socket_ );
#ifdef _WIN32
		WSACleanup();
#endif
		return false;
	}

	// Listen
	if ( listen( server_socket_, 3 ) == SOCKET_ERROR )
	{
		DriverLog( "HandTrackingListener: Failed to listen on socket" );
		closesocket( server_socket_ );
#ifdef _WIN32
		WSACleanup();
#endif
		return false;
	}

	DriverLog( "HandTrackingListener: Listening on port %d", port_ );

	// Start listening thread
	is_running_ = true;
	listen_thread_ = std::thread( &HandTrackingListener::ListenThread, this );

	return true;
}

void HandTrackingListener::Stop()
{
	if ( is_running_.exchange( false ) )
	{
		// Close sockets
		if ( client_socket_ != INVALID_SOCKET )
		{
			closesocket( client_socket_ );
			client_socket_ = INVALID_SOCKET;
		}
		if ( server_socket_ != INVALID_SOCKET )
		{
			closesocket( server_socket_ );
			server_socket_ = INVALID_SOCKET;
		}

		// Wait for thread to finish
		if ( listen_thread_.joinable() )
		{
			listen_thread_.join();
		}

#ifdef _WIN32
		WSACleanup();
#endif

		DriverLog( "HandTrackingListener: Stopped" );
	}
}

void HandTrackingListener::ListenThread()
{
	DriverLog( "HandTrackingListener: Thread started" );

	while ( is_running_ )
	{
		// Accept connection
		DriverLog( "HandTrackingListener: Waiting for client connection..." );
		struct sockaddr_in client_addr;
		socklen_t client_addr_len = sizeof( client_addr );
		client_socket_ = accept( server_socket_, (struct sockaddr *)&client_addr, &client_addr_len );

		if ( client_socket_ == INVALID_SOCKET )
		{
			if ( is_running_ )
			{
				DriverLog( "HandTrackingListener: Failed to accept connection" );
			}
			break;
		}

		DriverLog( "HandTrackingListener: Client connected" );

		// Receive data
		char buffer[ 2048 ];
		while ( is_running_ )
		{
			memset( buffer, 0, sizeof( buffer ) );
			int recv_size = recv( client_socket_, buffer, sizeof( buffer ) - 1, 0 );

			if ( recv_size > 0 )
			{
				buffer[ recv_size ] = '\0';
				std::string data( buffer );

				// Split by newlines in case multiple messages were sent
				size_t pos = 0;
				while ( ( pos = data.find( '\n' ) ) != std::string::npos )
				{
					std::string line = data.substr( 0, pos );
					if ( !line.empty() )
					{
						ProcessHandData( line );
					}
					data.erase( 0, pos + 1 );
				}
				// Process remaining data if any
				if ( !data.empty() )
				{
					ProcessHandData( data );
				}
			}
			else if ( recv_size == 0 )
			{
				DriverLog( "HandTrackingListener: Client disconnected" );
				break;
			}
			else
			{
				if ( is_running_ )
				{
					DriverLog( "HandTrackingListener: Receive error" );
				}
				break;
			}
		}

		closesocket( client_socket_ );
		client_socket_ = INVALID_SOCKET;
	}

	DriverLog( "HandTrackingListener: Thread stopped" );
}

void HandTrackingListener::ProcessHandData( const std::string &data )
{
	// Parse protocol string: HAND:LEFT,X:0.5,Y:0.3,Z:-0.2,QW:1.0,QX:0.0,QY:0.0,QZ:0.0,TRIGGER:0.8,GRIP:0.0,GESTURE:POINT
	std::map<std::string, std::string> params = ParseProtocolString( data );

	// Determine which hand this is for
	MyControllerDeviceDriver *controller = nullptr;
	if ( params[ "HAND" ] == "LEFT" )
	{
		controller = left_controller_;
	}
	else if ( params[ "HAND" ] == "RIGHT" )
	{
		controller = right_controller_;
	}

	if ( controller == nullptr )
	{
		return;
	}

	// Update position
	if ( params.count( "X" ) && params.count( "Y" ) && params.count( "Z" ) )
	{
		float x = std::stof( params[ "X" ] );
		float y = std::stof( params[ "Y" ] );
		float z = std::stof( params[ "Z" ] );
		controller->UpdateHandPosition( x, y, z );
	}

	// Update rotation
	if ( params.count( "QW" ) && params.count( "QX" ) && params.count( "QY" ) && params.count( "QZ" ) )
	{
		float qw = std::stof( params[ "QW" ] );
		float qx = std::stof( params[ "QX" ] );
		float qy = std::stof( params[ "QY" ] );
		float qz = std::stof( params[ "QZ" ] );
		controller->UpdateHandRotation( qw, qx, qy, qz );
	}

	// Update trigger
	if ( params.count( "TRIGGER" ) )
	{
		float trigger = std::stof( params[ "TRIGGER" ] );
		controller->UpdateTriggerValue( trigger );
	}

	// Update grip
	if ( params.count( "GRIP" ) )
	{
		float grip = std::stof( params[ "GRIP" ] );
		controller->UpdateGripValue( grip );
	}
}

std::map<std::string, std::string> HandTrackingListener::ParseProtocolString( const std::string &data )
{
	std::map<std::string, std::string> params;
	std::istringstream stream( data );
	std::string token;

	while ( std::getline( stream, token, ',' ) )
	{
		size_t colon_pos = token.find( ':' );
		if ( colon_pos != std::string::npos )
		{
			std::string key = token.substr( 0, colon_pos );
			std::string value = token.substr( colon_pos + 1 );
			params[ key ] = value;
		}
	}

	return params;
}