from boa.builtins import sha256
from boa.interop.System.ExecutionEngine import GetScriptContainer, GetCallingScriptHash, GetEntryScriptHash, \
    GetExecutingScriptHash
from boa.interop.System.Transaction import GetTransactionHash
from boa.interop.System.Blockchain import GetHeight
from boa.interop.System.Runtime import GetTime, Serialize, Notify, CheckWitness
from boa.interop.Ontology.Runtime import GetCurrentBlockHash
from boa.interop.System.App import RegisterAppCall
from boa.interop.System.Storage import GetContext, Get, Put,Delete
from boa.builtins import ToScriptHash, state, concat
from boa.interop.Ontology.Native import Invoke

OntContract = ToScriptHash("AFmseVrdL9f9oyCzZefL9tG6UbvhUMqNMV")
# ONG Big endian Script Hash: 0x0200000000000000000000000000000000000000
OngContract = ToScriptHash("AFmseVrdL9f9oyCzZefL9tG6UbvhfRZMHJ")

superadmin = ToScriptHash("AQyjYLQNRXtjr6cPoru1vpCTwehg6EQPCs")

teamaddress = ToScriptHash("AQyjYLQNRXtjr6cPoru1vpCTwehg6EQPCs")

testaddress = ToScriptHash("AHdVYY3oCPho1JmwYYmaPYUTXLsZXMAYL3")

ctx = GetContext()
FEE = 2


BALANCE_PREFIX = bytearray(b'\x01')
GUESS_PREFIX = bytearray(b'\x02')
BET_ID_PREFIX = bytearray(b'\x03')

FACTOR = 100000000

ONG = 1
ONT = 2
TNT = 3
TONT = 4

DICE_MAX = 96
DICE_MIN = 2

GAME_TOKEN_PEER_ONT = 10
GAME_TOKEN_PEER_ONG = 20  # 挖矿所用的分发的比例，每20个ong得1个token
INVITER_FEE = 200  # 邀请者，返利比例投注额的0.5%

ONG_MIN = 100000000  # bigerinteger充当小数
OPE4_MIN = 1000000000
TONT_MIN = 100000000


#error code定义

ERROR_AMONT = 1  #错误的下注额，小于最小下注额
ERROR_NUMBER = 2 #错误的下注数字，范围不在最小到最大数字之间
ERROR_ADDRESS = 3 #账户地址出错
ERROR_BANLANCE = 4 #账户余额不足
ERROR_TONT_WITHDRAW = 5 #提取TONT出错，提取数量必须为整数
ERROR_AUTH = 6#认证失败

SUCCESS_RECHARGE = 10 #
SUCCESS_Withdraw = 11 #

OEP4Contract = RegisterAppCall('49f0908f08b3ebce1e71dc5083cb9a8a54cc4a24', 'operation', 'args')


def Main(opration, args):
    if IsFromContract():
        return False

    if opration == "Guess":
        if len(args[0]) != 20:
            ErrorNotify(ERROR_ADDRESS)
            return False
        if CheckWitness(args[0]):
            if len(args) == 5:
                if len(args[4]) != 20:
                    return Guess(args[0], args[1], args[2], args[3], teamaddress)
                return Guess(args[0], args[1], args[2], args[3], args[4])
            if len(args) == 4:
                return Guess(args[0], args[1], args[2], args[3], teamaddress)
        return False
    if opration == "GetToken":
        return GetToken(args[0], args[1])
        
    if opration == "Withdraw":
        if len(args) != 2:
            return False
        if len(args[0]) != 20:
            ErrorNotify(ERROR_ADDRESS)
            return False
        return Withdraw(args[0],args[1])
    
    if opration == "banlanceTONT":
        if len(args) != 1:
            return False
        return banlanceTONT(args[0])
    
    if opration == "Recharge":
        if len(args) != 3:
            return False
        return Recharge(args[0],args[1],args[2])

    if opration == "Init":
        return Init()
    return False


def Init():
    constracthash = GetExecutingScriptHash()
    key = concat(BALANCE_PREFIX,constracthash)
    tobla = GetStorage(key)
    tobla = tobla + 1000 * FACTOR
    PutStorage(key,tobla)
    key2 = concat(BALANCE_PREFIX,superadmin)
    PutStorage(key2,1000*FACTOR)
    key3 = concat(BALANCE_PREFIX,testaddress)
    PutStorage(key3,1000*FACTOR)
    return True


def Guess(player, tokentype, number, amount, inviter):
    if tokentype == ONG:
        return guessForONG(player, number, amount, inviter)
    if tokentype == TONT:
        return guessForTONT(player, number, amount, inviter)
    if tokentype == TNT:
        return guessForOEP4(player, number, amount, inviter)
    return False



def guessForONG(player, number, amount, inviter):
    constracthash = GetExecutingScriptHash()
    #bla = balanceOf(constracthash, ONG)
    #ONG_max = bla / 100
    if amount < ONG_MIN: #or amount > ONG_max:
        ErrorNotify(ERROR_AMONT)
        return False
    if CheckRange(number) == False:
        ErrorNotify(ERROR_NUMBER)
        return False

    if transferONG(player, constracthash, amount) == False:  # 转移投注金额
        ErrorNotify(ERROR_BANLANCE)
        return False

    id = Get(ctx, BET_ID_PREFIX)
    Put(ctx, BET_ID_PREFIX, id + 1)  # 游戏次数

    sysnumber = GeneratorRandom(id)

    if number > sysnumber:
        winreward = GetBetReward(number, amount)
        transferONG(constracthash, player, winreward)
    
    Notify(['guess', ONG,player, amount, id + 1, number, sysnumber])
    rewardToken(player, constracthash, amount, ONG)
    if inviter != player:
        rewardInviterFEE(inviter, constracthash, amount, TNT)
    else:
        rewardInviterFEE(teamaddress, constracthash, amount, TNT)
    return True


def guessForTONT(player, number, amount, inviter):
    constracthash = GetExecutingScriptHash()
    #bla = balanceOf(constracthash, TONT)
    #TONT_max = bla / 100
    if amount < TONT_MIN: #or amount > TONT_max:
        ErrorNotify(ERROR_AMONT)
        return False
    if CheckRange(number) == False:
        ErrorNotify(ERROR_NUMBER)
        return False

    playbla = balanceOf(player, TONT)
    if playbla < amount:
        ErrorNotify(ERROR_BANLANCE)
        return False

        
    id = Get(ctx, BET_ID_PREFIX)
    Put(ctx, BET_ID_PREFIX, id + 1)  # 游戏次数

    sysnumber = GeneratorRandom(id)

    if number > sysnumber:
        winreward = GetBetReward(number, amount)
        win = winreward - amount
        transferTONT(constracthash,player,win)
    else:
        transferTONT(player,constracthash,amount)
    
    Notify(['guess', TONT,player, amount, id + 1, number, sysnumber])
    rewardToken(player, constracthash, amount, TONT)
    if inviter != player:
        rewardInviterFEE(inviter, constracthash, amount,TNT)
    else:
        rewardInviterFEE(teamaddress, constracthash, amount, TNT)
    return True


def guessForOEP4(player, number, amount, inviter):
    constracthash = GetExecutingScriptHash()
    #bla = balanceOf(constracthash, TNT)
    #OEP_MAX = bla / 100
    if amount < OPE4_MIN: #or amount > OEP_MAX:
        ErrorNotify(ERROR_AMONT)
        return False
    if CheckRange(number) == False:
        ErrorNotify(ERROR_NUMBER)
        return False

    playbla = balanceOf(player, TNT)
    if playbla < amount:
        ErrorNotify(ERROR_BANLANCE)
        return False

    id = Get(ctx, BET_ID_PREFIX)
    Put(ctx, BET_ID_PREFIX, id + 1)  # 游戏次数

    sysnumber = GeneratorRandom()

    if number > sysnumber:
        winreward = GetBetReward(number, amount)
        win = winreward - amount
        transferOEP4(constracthash, player, win)
    else:
        transferOEP4(player, constracthash, amount)
    Notify(['guess', TNT, player,amount, id + 1, number, sysnumber])
    # rewardInviterFEE(inviter,constracthash,amount,TNT)
    return True


def rewardInviterFEE(inviter, constracthash, playeramount, tokenType):
    inv = playeramount / INVITER_FEE
    if tokenType == ONG:
        transferONG(constracthash, inviter, inv)
        return True
    if tokenType == TONT:
        transferTONT(constracthash,inviter,inv)
    if tokenType == TNT:
        transferOEP4(constracthash,inviter,inv)
        return True
    return False


def rewardToken(player, constracthash, amount, tokenType):
    rewad = 0
    if tokenType == ONG:
        rewad = amount / GAME_TOKEN_PEER_ONG
    if tokenType == TONT:
        rewad = amount  / GAME_TOKEN_PEER_ONT

    bla = banlanceOEP4(constracthash)
    #Notify([bla, rewad])
    if bla > rewad:
        transferOEP4(constracthash, player, rewad)
    if bla > 0 and bla < rewad:
        transferOEP4(constracthash, player, bla)
    if bla <= 0:
        return False

    return True


def balanceOf(address, tokenType):
    if tokenType == ONG:
        param = state(address)
        res = Invoke(0, OngContract, 'balanceOf', param)
        return res
    if tokenType == ONT:
        param = state(address)
        res = Invoke(0, OntContract, 'balanceOf', param)
        return res
    if tokenType == TNT:
        return banlanceOEP4(address)
    if tokenType == TONT:
        return banlanceTONT(address)
    return 0


def CheckRange(number):
    if number > DICE_MAX or number < DICE_MIN:
        return False
    return True


def transferONG(fromaddr, toaddr, amount):
    param = state(fromaddr, toaddr, amount)
    res = Invoke(0, OngContract, "transfer", [param])
    return res
    pass


def transferONT(fromaddr, toaddr, amount):
    param = state(fromaddr, toaddr, amount)
    res = Invoke(0, OntContract, "transfer", [param])
    return res

def transferTONT(fromaddr,toaddr,amount):
    fkey = concat(BALANCE_PREFIX,fromaddr)
    tkey = concat(BALANCE_PREFIX,toaddr)
    fbla = GetStorage(fkey)

    if amount > fbla:
        return False
    
    tbla = GetStorage(tkey)
    PutStorage(tkey,tbla+amount)
    fbla = fbla - amount
    PutStorage(fkey,fbla)
    return True
def transferOEP4(fromaddr, toaddr, amount):
    params = [fromaddr, toaddr, amount]
    res = OEP4Contract("transfer", params)
    return res


def banlanceOEP4(addresss):
    params = [addresss]
    return OEP4Contract("balanceOf", params)

def banlanceTONT(address):
    key = concat(BALANCE_PREFIX,address)
    return GetStorage(key)

def GetBetReward(roll_border, amount):
    roll_border = roll_border - 1 #1-100,算法是基于0-99的
    reward_amt = amount * (100 - FEE) / roll_border
    return reward_amt


def IsFromContract():
    callerHash = GetCallingScriptHash()
    entryHash = GetEntryScriptHash()
    if callerHash != entryHash:
        return True
    return False


def GeneratorRandom(id):
    txid = GetTransactionHash(GetScriptContainer())

    blockHeigt = GetHeight() + 1
    blockTime = GetTime()
    blockHash = GetCurrentBlockHash()

    sysseed = [0, id, blockHeigt, blockTime, blockHash]
    sysseed = sha256(Serialize(sysseed))

    resseed = sha256(Serialize([txid, sysseed]))

    resseed = sha256(Serialize([resseed, resseed]))

    res = abs(resseed)
    number = res % 100
    number = number + 1
    return number


def GetToken(tokentype, amount):
    if (CheckWitness(superadmin)):
        if ONT == tokentype:
            constracthash = GetExecutingScriptHash()
            transferONT(constracthash, superadmin, amount)
            return True
        if ONG == tokentype:
            constracthash = GetExecutingScriptHash()
            transferONG(constracthash, superadmin, amount)
            return True
        if TNT == tokentype:
            constracthash = GetExecutingScriptHash()
            transferOEP4(constracthash, superadmin, amount)
            return True
        return False

    return False
    
def Withdraw(address, amount):
    if len(address) != 20:
        return False
    if CheckWitness(address) != True:
        return False
    if amount % FACTOR != 0:
        ErrorNotify(ERROR_TONT_WITHDRAW)
        return False
    blakey = concat(BALANCE_PREFIX, address)
    fromBalance = Get(ctx, blakey)

    if amount > fromBalance:
        ErrorNotify(ERROR_BANLANCE)
        return False

    ontam = amount / FACTOR
    constracthash = GetExecutingScriptHash()
    if transferONT(constracthash, address, ontam):
        if amount == fromBalance:
            Delete(ctx, blakey)
        else:
            Put(ctx, blakey, fromBalance - amount)
        Notify(["success", ontam])
        return True
    return False

def Recharge(fromaddr,toaddr,amount):

    if len(fromaddr) != 20 or len(toaddr) != 20:
        ErrorNotify(ERROR_ADDRESS)
        return False
    
    if CheckWitness(fromaddr) != True:
        ErrorNotify(ERROR_AUTH)
        return False

    constracthash = GetExecutingScriptHash()
    res = transferONT(fromaddr,constracthash,amount)

    if res != True:
        ErrorNotify(ERROR_BANLANCE)
        return False

    key = concat(BALANCE_PREFIX,toaddr)
    tobla = GetStorage(key)
    tobla = tobla + amount * FACTOR
    PutStorage(key,tobla)
    Notify(['success',amount])

    return True
    

def PutStorage(key,content):
    Put(ctx,key,content)

def GetStorage(key):
    return Get(ctx,key)

def ErrorNotify(errorInfo):
    Notify(["error",errorInfo])