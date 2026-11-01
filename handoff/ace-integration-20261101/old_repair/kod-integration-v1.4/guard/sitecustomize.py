import sys
def guard(event,args):
 if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','socket.bind'):
  raise RuntimeError('OFFLINE_TEST_GUARD: network prohibited')
sys.addaudithook(guard)
