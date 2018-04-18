# Developed from the draft phase 1 spec: https://ethresear.ch/t/sharding-phase-1-spec/1407
# As well as the validator_manager_contract:
# https://github.com/ethereum/py-evm/blob/sharding/evm/vm/forks/sharding/contracts/validator_manager.v.py

# Copyright: Unlicense, no rights reserved. Author: James Ray

# On events, see https://github.com/ethereum/vyper/blob/master/docs/logging.rst
# Events
CollationHeaderAdded: event({
    shard_id: bytes[256],
    parent_hash: bytes32,
    chunk_root: bytes32,
    period: int128,
    height: int128,
    proposer_address: address,
    proposer_bid: uint256,
    proposer_signature: bytes[8192] # 1024*8 for general signature schemes
})

RegisterNotary: event({
    pool_index: int128,
    notary_address: indexed(address),
    deregistered: indexed(int128),
    collation_deposit: indexed(wei_value)
})

DeregisterNotary: event({
    pool_index: int128, 
    notary_address: indexed(address),
    deregistered: indexed(int128)
})

ReleaseNotary: event({
    pool_index: int128, 
    notary_address: indexed(address),
    deregistered: indexed(int128)
})

RegisterProposer: event({
    proposer_address: address,
    deregistered: indexed(int128),
    proposer_deposit: indexed(wei_value)
})

DeregisterProposer: event({
    proposer_address: address,
    deregistered: indexed(int128)
})

ReleaseProposer: event({
    proposer_address: address,
    deregistered: indexed(int128),
    proposer_balance: indexed(wei_value)
})


# Parameters
#-----------

# latest_block_number: uint256

## Shards
#--------

# Sharding Manager Contract (SMC) address on the mainnet. TBD
smc_address: address

# The most significant byte of the shard ID, with most significant bit 0 for 
# mainnet and 1 for testnet. Provisionally NETWORK_ID := 0b1000_0001 for the 
# phase 1 testnet.
network_ID: bytes[8]
zero_address: address
bytes30_of_zeros: bytes[240]
shard_id_int128: int128

# Number of shards
shard_count: int128

# Number of blocks in one period
period_length: int128

# The lookahead time, denominated in periods, for eligible notaries to perform 
# windback and select proposals. Provisionally LOOKAHEAD_LENGTH := 4, 
# approximately 5 minutes.
# Number of periods ahead of current period, which the contract
# is able to return the notary of that period
lookahead_length: int128

windback_length: int128

## Collations
#------------
collation_size: int128
chunk_size: int128
notary_subsidy: decimal
notary_address: address

## Registries
#------------
notary_deposit: wei_value
proposer_deposit: wei_value
min_proposer_balance: decimal
notary_lockup_length: int128
proposer_lockup_length: int128
pool_index_temp: int128
proposer_address: address

activate_notary_num: int128
all_notary_slots_num: int128
notary_pool: public({
    # array of active notary addresses
    notary_pool_arr: address[int128],
    # size of the notary pool
    notary_pool_len: int128,
    # Stack of empty notary slot indices caused by the function
    # degister_notary().
    empty_slots_stack: int128[int128],
    # The top index of the stack in empty_slots_stack.
    empty_slots_stack_top: int128
})

# Collation headers
collation_header: public({
# Sharding participants have light-client access to collation headers via the 
# HeaderAdded logs produced by the addHeader method. The header fields are:
    # shard_id: uint256,  # pointer to shard
    # shard_id: bytes32
    shard_id: bytes[256],
    parent_hash: bytes32,  # pointer to parent header
    chunk_root: bytes32, # pointer to collation body
    period: int128,
    height: int128,
    proposer_address: address,
    proposer_bid: uint256,
    proposer_signature: bytes32,
})#[bytes32][int128])

# With each field as a bytes32 for concatentation prior to hashing
# 8 members * 32 bytes/member * 8 bits/bytes = 2048
collation_header_bytes: bytes[2048]
header_hash: bytes32

# from VMC: TODO: determine the signature of the above logs 
# `RegisterNotary` and `DeregisterNotary`

notary_registry: public({
    deregistered: int128,
    # deregistered is 0 for not yet deregistered notaries.
    pool_index: int128
}[address])

proposer_registry: public({
    deregistered: int128,
    balances: wei_value
}[address])

collation_trees_struct: public({
    # The collation tree of a shard maps collation hashes to previous collation
    # hashes truncated to 24 bytes packed into a bytes32 with the collation
    # height in the last 8 bytes.
    collation_trees: bytes32[bytes32][uint256],
    # This contains the period of the last update for each shard.
    last_update_periods: int128[uint256]
})

availability_challenges_struct: public({
    # availability_challenges:
    # availability challenges counter
    availability_challenges_len: int128
})

@public
def __init__():
    # Shards
    #self.smc_address = 
    self.network_ID = "10000001"
    self.shard_count = 100			# shards
    self.period_length = 5			# block times
    self.lookahead_length = 4		# periods
    self.windback_length = 25		# collations

    # Collations
    self.collation_size	= 1048576	# 2^20 bytes
    self.chunk_size = 32			# bytes
    self.notary_subsidy = 0.001 	# vETH
    self.notary_pool.notary_pool_len = 0		
    self.notary_pool.empty_slots_stack_top = 0
    
    # Registries
    self.notary_deposit = 1000000000000000000000 		# 10^21 wei = 1000 ETH
    #notary_subsidy = 1000000000000000				    # 10^15 wei = 0.001 ETH
    self.min_proposer_balance = 10000000000000			# 10^17 wei = 0.1 ETH
    self.notary_lockup_length = 16128					# periods
    self.proposer_lockup_length = 48					# periods
    # 10 ** 20 wei = 100 ETH
    #self.deposit_size = 100000000000000000000
    # 40 zeros after x, 4 bytes per digit, 160 bits
    self.zero_address = 0x0000000000000000000000000000000000000000
    # 60 zeros after x, 30 bytes
    self.bytes30_of_zeros \
        = "0x000000000000000000000000000000000000000000000000000000000000"

#@private
#def get_latest_block_number() -> uint256:
#   Link: https://api.etherscan.io/api?module=proxy&action=eth_blockNumber
#    &apikey='your API key'
#    payload = {'module': 'proxy', 'action': 'eth_blockNumber', \
#        'apikey' : your API key}
#   requests...json() returns a string containing a hexadecimal number, e.g. 
#       "0x51ac9f". Need to convert it to a uint256.
#   There is no support for strings, so working with this result doesn't seem 
#   feasible, e.g. you can't slice the result or convert it to a uint256.
#    latest_block_number = convert(slice(requests.get(\
#        "https://api.etherscan.io/api", params=payload).json()\
#        ["result"]), 'bytes')
#    return latest_block_number

# Try to find out how to use an oracle instead.

# Apparently block.number will suffice, but check.

# Checks if empty_slots_stack_top is empty    
@private
def is_stack_empty() -> bool:
    return (self.notary_pool.empty_slots_stack_top == 0)

# Pushes one num to empty_slots_stack. Why not just use the push method?
@private
def stack_push(index: int128):
    self.notary_pool.empty_slots_stack[self.notary_pool \
        .empty_slots_stack_top] = index
    #(self.notary_pool.empty_slots_stack[
    #TODO: re-add this: self.notary_pool.empty_slots_stack_top] = index)
    self.notary_pool.empty_slots_stack_top += 1
    
# Pops one num out of empty_slots_stack. Why not just use the pop method?
@private
def stack_pop() -> int128:
    if self.is_stack_empty():
        return -1
    self.notary_pool.empty_slots_stack_top -= 1
    return (self.notary_pool.empty_slots_stack[self.notary_pool.
        empty_slots_stack_top])

# What if someone wants to (de)register a notary or a proposer on  
# someone else's behalf, or wants to register with a different  
# address from msg.sender, but that they own? For simplicity and
# security just allow only msg.sender to (de)register msg.sender.

# Register a notary. Adds an entry to notary_registry, updates the
# notary pool (notary_pool, notary_pool_len, etc.), locks a deposit
# of size NOTARY_DEPOSIT, and returns True on success. Checks:

#    Deposit size: msg.value >= NOTARY_DEPOSIT
#    Uniqueness: notary_registry[msg.sender] does not exist

# Checks if empty_slots_stack_top is empty
@public
@payable
def register_notary() -> bool:
    self.notary_address = msg.sender
    assert msg.value >= self.notary_deposit
    # TODO: make sure that it will return 0 if it doesn't exist, not None.
    assert not self.notary_registry[self.notary_address].pool_index == 0
    # Find the empty slot index in the notary pool.
    if not self.is_stack_empty():
        self.pool_index_temp = self.stack_pop()	
    else:
        self.pool_index_temp = self.notary_pool.notary_pool_len 
        # notary_pool_arr indices are from 0 to notary_pool_len - 1. ;)
    self.notary_registry[self.notary_address].deregistered = 0 
    self.notary_registry[self.notary_address].pool_index \
        = self.pool_index_temp

    self.notary_registry[self.notary_address] = {
        deregistered : 0,
        pool_index : self.pool_index_temp
    }

    (log.RegisterNotary(self.pool_index_temp, self.notary_address,
        self.notary_registry[self.notary_address].deregistered, \
        self.notary_deposit))

    return True
    
    
# Verifies that `msg.sender == notaries[notary_index].addr`. If it is then
# remove the notary rom the notary pool and refund the deposited ETH.
@public
def deregister_notary() -> bool:
    self.notary_address = msg.sender
    assert self.notary_registry[self.notary_address].deregistered == 0
    self.notary_registry[self.notary_address].deregistered \
        = self.notary_lockup_length

    self.stack_push(self.notary_registry[self.notary_address].pool_index)
    self.notary_pool.notary_pool_len -= 1
    
    log.DeregisterNotary(self.notary_registry[self.notary_address]\
        .pool_index, self.notary_address, \
        self.notary_registry[self.notary_address].deregistered)

    return True

# Removes an entry from notary_registry, releases the notary deposit, and
# returns True on success. Checks:

#   Authentication: notary_registry[msg.sender] exists
#   Deregistered: notary_registry[msg.sender].deregistered != 0
#   Lockup: floor(collation_header.number / period_length) 
#       > notary_registry[msg.sender].deregistered + notary_lockup_length
    
@public
@payable
def release_notary() -> bool:
    self.notary_address = msg.sender
    assert self.notary_registry[self.notary_address].deregistered != 0
    assert floor(block.number / self.period_length) > self.notary_registry\
        [msg.sender].deregistered + self.notary_lockup_length
        
    send(self.notary_address, self.notary_deposit)
    self.notary_registry[self.notary_address] = {
        deregistered : 0,
        pool_index : 0
    }

    log.ReleaseNotary(self.notary_registry[self.notary_address]\
        .pool_index, self.notary_address, \
        self.notary_registry[self.notary_address].deregistered)
    
    return True
    
# register_proposer() returns bool: Equivalent of register_notary(),
# without the notary pool updates.

@public
@payable
def register_proposer() -> bool:
    self.proposer_address = msg.sender
    # Make sure the proposer doesn't already exist in the registry.
    assert not self.proposer_registry[self.proposer_address].balances != 0
    assert msg.value >= self.proposer_deposit
    # TODO: make sure that it will return 0 if it doesn't exist, not None.

    self.proposer_registry[self.proposer_address] = {
        deregistered : 0,
        balances : msg.value
    }

    log.RegisterProposer(self.proposer_address,\
        self.proposer_registry[self.proposer_address].deregistered, msg.value)

    return True

# deregister_proposer() returns bool: Equivalent to  
# deregister_notary(), without the notary pool updates.

@public
def deregister_proposer() -> bool:
    self.proposer_address = msg.sender
    assert self.proposer_registry[self.proposer_address].deregistered != 0
    self.proposer_registry[self.proposer_address].deregistered \
        = self.proposer_lockup_length
    
    log.DeregisterProposer(self.proposer_address, \
        self.proposer_registry[self.proposer_address].deregistered)

    return True

# release_proposer() returns bool: Equivalent of release_notary().
# WARNING: The proposer balances need to be emptied before calling this method.
# Why? Can't they be cleared during the method?

@public
@payable
def release_proposer() -> bool:
    self.proposer_address = msg.sender
    assert self.proposer_registry[self.proposer_address].deregistered != 0
    
    assert floor(block.number / self.period_length) > self.notary_registry\
        [msg.sender].deregistered + self.notary_lockup_length
    send(self.proposer_address, self.proposer_registry\
        [self.proposer_address].balances)
        
    self.proposer_registry[self.proposer_address] = {
        deregistered : 0,
        balances : 0
    }

    log.ReleaseProposer(self.proposer_address, \
        self.proposer_registry[self.proposer_address].deregistered,\
        self.proposer_registry[self.proposer_address].balances)
    
    return True
   
# These will reduce boilerplate code but require assigning the original
# msg.sender from the calling function to a temporary variable before
# passing this variable to these function, which adds complexity.
# However, this is used in the 6 functions below, so should be done.
@public
def check_shard_id(shard_id: bytes[256]) -> bool:
    # doesn't work:
    # https://gitter.im/ethereum/vyper?at=5ac3508127c509a774d0df87
    # Compiler bug: 'ByteArrayType' object has no attribute 'positional'
    # Vyper doesn't support byte array comparisons,
    # https://gitter.im/ethereum/vyper?at=5ac49ba32b9dfdbc3a54621f
    assert convert(slice(shard_id, start = 0, len = 8), 'int128') == \
        convert(0b10000001, 'int128')
    # assert slice(shard_id, start = 8, len = 240) == self.bytes30_of_zeros
    # self.shard_id_int128 = convert(slice(shard_ID, start = 247, len = 8)), \
    #   'int128')
    # assert self.shard_id_int128 <= 100 and self.shard_id_int128 > 0
    return True

#def check_sender_in_proposer_registry(original_sender: address)
    
# proposer_add_balance(uint256 shard_id) returns bool: Adds msg.value to the
# balance of the proposer on shard_id, and returns True on success. Checks:
#    Shard: shard_id against NETWORK_ID and SHARD_COUNT
#    Authentication: proposer_registry[msg.sender] exists
@public
@payable
def proposer_add_balance(shard_id: bytes[256]) -> bool:
    assert self.check_shard_id(shard_id) == True
    
    # Again, this isn't the same as that it doesn't exist, TODO.
    assert self.proposer_registry[msg.sender].balances != 0
    
    self.proposer_registry[msg.sender].balances += msg.value
    
    return True
    
# proposer_withdraw_balance(uint256 shard_id) returns bool: Withdraws the 
# balance of a proposer on shard_id, and returns True on success. Checks:

#    Shard: shard_id against NETWORK_ID and SHARD_COUNT
#    Authentication: proposer_registry[msg.sender] exists
#   proposer_lockup_length

@public
@payable
def proposer_withdraw_balance(shard_id: bytes[256]) -> bool:
    assert self.check_shard_id(shard_id) == True
    
    # Again, this isn't the same as that it doesn't exist, TODO.
    assert self.proposer_registry[msg.sender].balances != 0
    
    self.proposer_address = msg.sender
    
    send(self.proposer_address, self.proposer_registry\
        [self.proposer_address].balances)
    
    return True

# Returns the current maximum index for notary mapping
@private
def get_notaries_max_index() -> int128:
    self.activate_notary_num = 0
    self.all_notary_slots_num = self.notary_pool.notary_pool_len \
        + self.notary_pool.empty_slots_stack_top
    
    # TODO: any better way to iterate the mapping?
    for i in range(1024):
        if i >= self.all_notary_slots_num:
            break
        if self.notary_pool.notary_pool_arr[i] != self.zero_address:
        #if self.notary_registry.pool_index != 0
            self.activate_notary_num += 1
    return self.activate_notary_num + self.notary_pool.empty_slots_stack_top

# Collation trees

# get_eligible_notary(uint256 shard_id, uint256 period) returns address: 
# Uses the blockhash at block number (period - LOOKAHEAD_LENGTH) 
# * PERIOD_LENGTH) and shard_id to pseudo-randomly select an eligible
# notary from the notary pool, and returns the address of the 
# eligible notary. 
# [TODO] Chance of being selected should be proportional to the notary's
# deposit. Should be able to return a value for the current period or any 
# future period up to.
# Checks:
#       Shard: shard_id against NETWORK_ID and SHARD_COUNT
#       Period: period == floor(block.number / PERIOD_LENGTH)
#       Non-empty pool: notary_pool_len > 0

@public
#@constant
def get_eligible_notary(shard_id: bytes[256], period: uint256 ) -> address:
    # This won't work if it's a constant function:
    # assert self.check_shard_id(shard_id) == True
    # assert slice(shard_id, start = 0, len = 8) == "10000001"
    # assert slice(shard_id, start = 8, len = 240) == self.bytes30_of_zeros
    # self.shard_id_int128 = convert(slice(shard_ID, start = 247, len = 8)), \
    #   'int128')
    # assert self.shard_id_int128 <= 100 and self.shard_id_int128 > 0    
    assert uint256_ge(period, convert(self.lookahead_length, 'uint256'))
    # assert period == floor(block.number / self.period_length)
    assert period == convert(floor(block.number / self.period_length), 'uint256')
    # assert convert(period, 'int128') == floor(block.number / self.period_length)
    # assert uint256_le(
    #    convert(uint256_mul(\
    #        uint256_sub(period, convert(self.lookahead_length,'uint256')) \
    #    , convert(self.period_length, 'uint256'))
    # , convert(block.number, 'uint256')),'uint256')
    assert self.notary_pool.notary_pool_len > 0
    return self.notary_pool.notary_pool_arr[
        convert(
            uint256_mod(
                convert(
                    sha3(
                        concat(
                            # TODO: should check further if this can be 
                            # further optimized or not e.g. be able to
                            # get the proposer of one period earlier.
                            # causes a compiler bug error: 'ByteArrayType'
                            # object has no attribute 'positional'
                            # https://gitter.im/ethereum/vyper?at=5ac48ab31130fe3d369dabfb
                            "tmp"#blockhash((convert(period, 'int128') \
                            #    - self.lookahead_length) \
                            #    * self.period_length) \
                            # blockhash(uint256_mul(uint256_sub(period, \
                            #    convert(self.lookahead_length, 'uint256')) \
                            # , convert(self.period_length, 'uint256'))),
                            , shard_id \
                        )
                    )
                , 'uint256'),
                # can't call this in a constant function
                # despite this function being constant in the original
                # validator_manager_contract,
                # https://github.com/ethereum/py-evm/blob/sharding/evm/vm/forks/sharding/contracts/validator_manager.v.py
                # it seems that the constant decorator may need to be removed,
                # at least until another solution is found
                convert(self.get_notaries_max_index(), 'uint256'),
            )
        , 'int128')
    ]

# compute_header_hash(uint256 shard_id, bytes32 parent_hash, 
#       bytes32 chunk_root, uint256 period, address proposer_address,
#       uint256 proposer_bid) returns bytes32: Returns the header hash.
@public
def compute_header_hash(
        _shard_id: bytes[256],
        _parent_hash: bytes32,  # pointer to parent header
        _chunk_root: bytes32,   # pointer to collation body
        _period: int128,
        _height: int128,
        _proposer_address: address,
        _proposer_bid: uint256,
        _proposer_signature: bytes32,
    ) -> bytes32:
    assert self.check_shard_id(_shard_id) == True
    # Check if the header is valid
    assert block.number >= self.period_length
    assert _period == floor(block.number / self.period_length)
    # TODO: from VMC, replace
    # assert period_start_prevhash == blockhash(expected_period_number \
    #   * self.period_length - 1)
    # Maybe with:
    # assert period_start_prevhash == blockhash(period * self.period_length - 1)
    # Check if this header already exists
    self.collation_header_bytes = concat(
        _shard_id,
        _parent_hash,
        _chunk_root,
        convert(_period, 'bytes32'),
        convert(_height, 'bytes32'),
        convert(_proposer_address, 'bytes32'),
        convert(_proposer_bid, 'bytes32'),
        _proposer_signature
    )
    
    self.header_hash = sha3(self.collation_header_bytes)

    return self.header_hash

# add_header(bytes32 shard_id, bytes32 parent_hash, bytes32 chunk_root,
#       uint256 period, address proposer_address, uint256 proposer_bid,
#       bytes proposer_signature) returns bool: 
# Calls compute_header_hash(...), extends the collation tree of shard_id,
# burns the proposer_bid from the proposer’s balance at shard_id, issues
# a HeaderAdded log, and returns True on success. Checks:
#       Shard: shard_id against NETWORK_ID and SHARD_COUNT
#       Notary eligibility: msg.sender == get_eligible_notary(
#            shard_id, period)
#       Parent exists: collation_trees[shard_id]
#           [compute_header_hash(...)] exists
#       Correct period: period == floor(block.number / PERIOD_LENGTH)
#       Unique update: period != last_update_periods[shard_id]
#       Proposer balance: proposer_registry[proposer_address].balances
#           [shard_id] >= max(proposer_bid, MIN_PROPOSER_BALANCE)
#       Proposer signature: proposer_signature matches 
#           compute_header_hash(...) and proposer_address

# Slashing

# proposal_commitment_slashing(bytes32 shard_id, bytes32 collation_hash,
#       uint256 height, uint256 left_hash, uint256 right_hash, 
#       bytes signature) returns bool: 
# Slashes a notary that called add_header with a non-committed 
# proposal. Checks:
#       Shard: shard_id against NETWORK_ID and SHARD_COUNT
#       Collation tree: collation_trees[shard_id][collation_hash] exists
#       Height: collation_trees[shard_id][collation_hash] matches height
#       Signature: signature matches height, left_hash and right_hash
#       Slashing condition: left_hash < collation_hash and 
#           collation_hash < right_hash



#    availability_challenge(): TBD
#    availability_response(): TBD
#    availability_slashing(): TBD

# A nickname for this contract could be Nataraja, the Lord of Dance, 
# who is a symbolic form of God performing a dance 
# of bliss in which creation is created, preserved and dissolved.
# This nickname for the SMC seems appropriate, since it is managing 
# "universes" of shards. For unambiguity where necessary it can be called
# the Nataraja contract or the SMC.
