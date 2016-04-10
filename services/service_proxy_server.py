#!/usr/bin/python
#service_proxy_server.py
#
# <<<COPYRIGHT>>>
#
#
#
#

"""
.. module:: service_proxy_server

"""

from services.local_service import LocalService

def create_service():
    return ProxyServerService()
    
class ProxyServerService(LocalService):
    
    service_name = 'service_proxy_server'
    config_path = 'services/proxy-server/enabled'
    
    def init(self):
        # self.debug_level = 2
        self.log_events = True
    
    def dependent_on(self):
        return ['service_p2p_hookups',
                ]
        
    def enabled(self):
        from main import settings
        return settings.enableProxyServer()
    
    def start(self):
        from transport.proxy import proxy_router
        proxy_router.A('init')
        proxy_router.A('start')
        return True
    
    def stop(self):
        from transport.proxy import proxy_router 
        proxy_router.A('stop')
        proxy_router.Destroy()
        return True
    
    def request(self, request, info):
        from transport.proxy import proxy_router 
        proxy_router.A('request-route', (request, info))
        return None
    
    def cancel(self, request, info):
        from transport.proxy import proxy_router 
        proxy_router.A('cancel-route', (request, info))
        return None

    