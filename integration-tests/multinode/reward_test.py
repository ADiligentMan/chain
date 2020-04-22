#!/usr/bin/env python3
import os
import math
from chainrpc import RPC
from common import UnixStreamXMLRPCClient, wait_for_blocks, stop_node, wait_for_blocktime

'''
wait for first reward distribution (the second block)
check reward amount

wait for 5 blocks for byzantine fault detected
check jail status and slashing

wait for reward period for second reward distribution
check jailed node no reward
check slashing is added into reward amount
'''


def monetary_expansion(S, tau):
    period = 10
    Y = 365 * 24 * 60 * 60
    R = 0.45 * math.exp(-S / tau)
    N = int(S * (math.pow(1 + R, period / Y) - 1))
    return N - N % 10000


BASE_PORT = int(os.environ.get('BASE_PORT', 25560))
supervisor = UnixStreamXMLRPCClient('data/supervisor.sock')
rpc = RPC(BASE_PORT)
rpc2 = RPC(BASE_PORT + 20)
init_bonded = 90000000000000000

os.environ['ENCKEY'] = rpc.wallet.enckey()
bonded_staking = rpc.address.list()[0]

wait_for_blocks(rpc, 2, height=0)

# first reward distribution
# minted = 6978080000
minted = monetary_expansion(init_bonded * 2, 145000000000000000)

state = rpc.chain.staking(bonded_staking, height=2)
assert int(state['bonded']) == init_bonded + minted // 2

enckey2 = rpc2.wallet.enckey()
bonded_staking2 = rpc2.address.list(enckey=enckey2)[0]

state = rpc.chain.staking(bonded_staking2, height=2)
assert int(state['bonded']) == init_bonded + minted // 2

last_bonded = int(state['bonded'])

# wait for byzantine fault detected
wait_for_blocks(rpc, 5)
stop_node(supervisor, 'node1')

# jailed and slashed
slashed = int(last_bonded * 0.2)
state = rpc.staking.state(bonded_staking2)
assert state['validator']['jailed_until'] is not None
assert int(state['bonded']) == last_bonded - slashed

# wait for reward period, for second reward distribution
wait_for_blocktime(rpc, 10)
# minted = 6182420000
minted = monetary_expansion(last_bonded, int(145000000000000000 * 0.99986))

state = rpc.staking.state(bonded_staking2)
assert int(state['bonded']) == last_bonded - slashed, 'jailed node don\'t get rewarded'

state = rpc.staking.state(bonded_staking)
assert int(state['bonded']) == last_bonded + minted + slashed
