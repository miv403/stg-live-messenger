from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import socket
import time


class AllServicesListener(ServiceListener):
    """Service listener that collects all services of a given type without ID filtering."""
    
    def __init__(self):
        self.found_services = []
    
    def update_service(self, zc, type_, name):
        """Handle service update."""
        pass
    
    def remove_service(self, zc, type_, name):
        """Handle service removal."""
        # Remove from found_services if present
        self.found_services = [s for s in self.found_services if s['name'] != name]
    
    def add_service(self, zc, type_, name):
        """Handle new service discovery."""
        info = zc.get_service_info(type_, name)
        
        if info:
            addresses = ["%s" % socket.inet_ntoa(addr) 
                        for addr in info.addresses]
            
            info.server = str(info.server) if info.server else ""
            
            # Extract service name (first part before the dot)
            service_name = info.server.split('.')[0] if info.server else name.split('.')[0]
            
            service_info = {
                'name': service_name,
                'type': type_,
                'addresses': addresses,
                'port': info.port,
                'server': info.server
            }
            
            # Avoid duplicates
            if not any(s['name'] == service_name and s['addresses'][0] == addresses[0] 
                      for s in self.found_services):
                self.found_services.append(service_info)


class Client:
    """Client class for discovering and connecting to servers."""
    
    def __init__(self):
        """Initialize the client."""
        self.service_type = "_stgserver._tcp.local."
    
    def discover_servers(self, timeout=5):
        """Discover all available stgserver services on the LAN.
        
        Args:
            timeout: Time to wait for service discovery in seconds (default: 5)
            
        Returns:
            list: List of server dictionaries with keys: 'name', 'address', 'port', 'server'
                  Returns empty list if no services found
        """
        zc = Zeroconf()
        listener = AllServicesListener()
        browser = ServiceBrowser(zc, self.service_type, listener)
        
        # Wait for discovery
        time.sleep(timeout)
        
        # Close zeroconf (this will stop the browser)
        zc.close()
        
        # Format servers for UI
        servers = []
        for service in listener.found_services:
            servers.append({
                'name': service['name'],
                'address': service['addresses'][0] if service['addresses'] else 'N/A',
                'port': service['port'],
                'server': service['server']
            })
        
        return servers

