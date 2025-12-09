"""
Socket client for communication with SteamVR driver.
"""
import socket
import time
from typing import Optional


class SocketClient:
    """Handles socket communication with the SteamVR driver."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 65432, 
                 auto_reconnect: bool = True, reconnect_interval: float = 5.0):
        """
        Initialize socket client.
        
        Args:
            host: Server host address
            port: Server port
            auto_reconnect: Whether to automatically reconnect on connection loss
            reconnect_interval: Seconds between reconnection attempts
        """
        self.host = host
        self.port = port
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.last_reconnect_attempt = 0.0
        
    def connect(self) -> bool:
        """
        Connect to the server.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            if self.socket:
                self.close()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to SteamVR driver at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to {self.host}:{self.port}: {e}")
            self.connected = False
            return False
    
    def send(self, data: str) -> bool:
        """
        Send data to the server.
        
        Args:
            data: String data to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.connected:
            if self.auto_reconnect:
                current_time = time.time()
                if current_time - self.last_reconnect_attempt >= self.reconnect_interval:
                    self.last_reconnect_attempt = current_time
                    print("Attempting to reconnect...")
                    self.connect()
            
            if not self.connected:
                return False
        
        try:
            # Ensure data ends with newline for easier parsing
            if not data.endswith('\n'):
                data += '\n'
            
            self.socket.sendall(data.encode('utf-8'))
            return True
            
        except Exception as e:
            print(f"Error sending data: {e}")
            self.connected = False
            return False
    
    def close(self):
        """Close the socket connection."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        print("Socket closed")
    
    def is_connected(self) -> bool:
        """Check if socket is connected."""
        return self.connected
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
