import models.PortfolioModel, models.PositionModel, models.OrderModel, models.StrategyDataModel
import tables as pt
from optparse import OptionParser
import sys, time
import Portfolio, Position, Order, StrategyData


class Simulator():
    def __init__(self, cash, stocks, strategy, startTime, endTime, interval, minCom, comPerShare, isTable, maxEffect):
        # NOTE: As written currently, strategy is a method
        self.strategy = strategy
        self.startTime = startTime
        self.currTimestamp = startTime
        self.endTime = endTime
        self.interval = interval
        self.minCom = minCom
        self.comPerShare = comPerShare
        self.timeStampIndex = 0
        self.maxEffect = maxEffect
        self.times =  [] # eventual list for timestamps
        self.isTable = isTable # Need for getting volumes
        
        self.portfolio = Portfolio.Portfolio(cash, stocks)   #portfolioFile.createTable('/', 'portfolio', self.PortfolioModel)
        self.position = Position.Position()   #positionFile.createTable('/', 'position', self.PositionModel)
        self.order = Order.Order()   #orderFile.createTable('/', 'order', self.OrderModel)
        self.strategyData = StrategyData.StrategyData('models/PriceTestData.h5',isTable)   #strategyDataFile.createTable('/', 'strategyData', self.strategyDataModel)
    
    def addTimeStamps(self):
        temp = []

        if timersActive:
            print 'Generating valid timestamps'
            cnt = 0
            cycTime = time.time()
        for i in self.strategyData.strategyData.iterrows():
            if i['data/timestamp'] not in temp:
                temp.append(i['data/timestamp'])
            if timersActive:
                if(cnt%1000000==0):
                    print '%i rows finished: %i secs elapsed'%(cnt,time.time()-cycTime)
                cnt+=1
        if timersActive:
            print 'all rows added: %i secs elapsed'%(time.time()-cycTime)        
        temp.sort()
        return temp
    
    def calcCommission(self, volume):
        return max(minCom,volume * self.comPerShare)
    
    def getExecutionTimestamp(self):
        while self.times[self.timeStampIndex]<self.currTimestamp:
            self.timeStampIndex += 1
        idealTime = self.times[self.timeStampIndex+1]
        return idealTime
        
    def calcEffect(self, maxVol, shares):
        return float(shares)/maxVol * self.maxEffect
        
    def getVolumePerDay(self, symbol, timestamp):  
        # Call with startTime = endTime = desired timestamp to get just that timestamp
        stocks = self.strategyData.getStocks(timestamp, timestamp, symbol, self.isTable)
        myStockasDict = stocks[0] #Grab the first dictionary in the list
        vol = myStockasDict['volume'] # Get the volume
        return vol    
            
    def buyStock(self, newOrder):
        '''
        function takes in an instance of OrderDetails, executes the changes to the portfolio and adds the order to the order table
        newOrderDetails: an instance of OrderDetails representing the new order
        Note: The Order should not be added to the order table before calling this function
        '''
        
        #buyTransaction needs to be expanded and put in here instead.
        '''
        ORDER:
        row['shares'] = shares
        row['symbol'] = symbol
        row['order_type'] = orderType
        row['duration'] = duration
        row['timestamp'] = timestamp
        row['close_type'] = closeType
        '''  
        #purchase = Position(timestamp, self.symbol, quantity, price)
        #self.position.append(purchase)         
        #newOrder = self.order.addOrder(self.currTimestamp,newOrderDetails.shares,newOrderDetails.symbol,newOrderDetails.orderType,newOrderDetails.duration,newOrderDetails.closeType,newOrderDetails.limitPrice)
        ts = self.getExecutionTimestamp() #need a function to get the next available time we can trade
        maxVol4Day = self.getVolumePerDay(newOrder['symbol'], ts) # Should this be the trading timestamp or the current one?
        if newOrder['order_type'] == 'moo':
            #market order open
            price = strategyData.getPrice(ts, newOrder['symbol'], 'adj_open')
            if price == None:
                if noisy:
                    print "Price data unavailable for ts:",ts,'stock:',newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']
            else:
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                # New is cost the original total price (price * shares) + effect*Total Price
                # Basically, you raise the cost as you buy
                cost = (newOrder['shares'] * price + (newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']))) + self.calcCommission(newOrder['shares'])
                if(cost>self.portfolio.currCash):
                    #Not enough cash to buy stock
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = -price
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                self.portfolio.buyTransaction(newOrder)
                #add position
                self.position.addPosition(ts,newOrder['symbol'],newOrder['shares'],price)
        elif newOrder['order_type'] == 'moc':
            #market order close
            price = self.strategyData.getPrice(ts, newOrder['symbol'], 'adj_close')
            if price == None:
                if noisy:
                    print "Price data unavailable for ts:",ts,'stock:',newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']
            else: 
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                # New is cost the original total price (price * shares) + effect*Total Price
                # Basically, you raise the cost the more you buy.
                cost = (newOrder['shares'] * price + (newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']))) + self.calcCommission(newOrder['shares'])
                #print self.portfolio.currCash, self.calcCommission(newOrder['shares']), cost
                if(cost>self.portfolio.currCash):
                    #print newOrder
                    #Not enough cash to buy stock
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = -price
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                #print newOrder
                self.portfolio.buyTransaction(newOrder)
                #add position
                self.position.addPosition(ts,newOrder['symbol'],newOrder['shares'],price)
        elif newOrder['order_type'] == 'limit':
            #limit order
            price = newOrder['limit_price']
            if price == None:
                if noisy:
                    print "Price data unavailable for ts:",ts,'stock:',newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']
            else:
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                # New is cost the original total price (price * shares) + effect*Total Price
                # Basically, you raise the cost the more you buy.
                cost = (newOrder['shares'] * price + (newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']))) + self.calcCommission(newOrder['shares'])
                if ((newOrder['limit_price'] > strategyData.getPrice(ts, newOrder['symbol'], 'adj_high')) or ( newOrder['limit_price'] < strategyData.getPrice(ts, newOrder['symbol'], 'adj_low'))):
                    #limit price outside of daily range
                    return None
                if(cost>self.portfolio.currCash):
                    #Not enough cash to buy stock
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = -price
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                self.portfolio.buyTransaction(newOrder)
                #add position
                self.position.addPosition(ts,newOrder['symbol'],newOrder['shares'],price)
        elif newOrder['order_type'] == 'vwap':
            #volume weighted average price
            price = strategyData.getPrice(ts, newOrder['symbol'], 'adj_open')
            if price == None:
                if noisy:
                    print "Price data unavailable for ts:",ts,'stock:',newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']
            else:
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                price += strategyData.getPrice(ts, newOrder['symbol'], 'adj_close')
                price += strategyData.getPrice(ts, newOrder['symbol'], 'adj_high')
                price += strategyData.getPrice(ts, newOrder['symbol'], 'adj_low')
                price = price / 4.
                # New is cost the original total price (price * shares) + effect*Total Price
                # Basically, you raise the cost the more you buy.
                cost = (newOrder['shares'] * price + (newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']))) + self.calcCommission(newOrder['shares'])
                if(cost>self.portfolio.currCash):
                    #Not enough cash to buy stock
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = -price
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                self.portfolio.buyTransaction(newOrder) 
                #add position
                self.position.addPosition(ts,newOrder['symbol'],newOrder['shares'],price)
        else:
            #throw invalid type error
            #print type(newOrder)
            raise TypeError("Not an existing trade type '%s'." % str(newOrder['order_type']))
        newOrder.update()
        self.order.order.flush()
        return price
    
    def sellStock(self,newOrder):
        """
        Comments 'n stuff go here.
        """
        #sellTransaction needs to be expanded and put here instead.
        #newOrder = self.order.addOrder(self.currTimestamp,newOrderDetails.shares,newOrderDetails.symbol,newOrderDetails.orderType,newOrderDetails.duration,newOrderDetails.closeType,newOrderDetails.limitPrice)
        ts = self.getExecutionTimestamp() #need a function to get the next available time we can trade
        maxVol4Day = self.getVolumePerDay(newOrder['symbol'], ts)    
        if newOrder['order_type'] == 'moo':
            #market order open
            price = self.strategyData.getPrice(ts, newOrder['symbol'], 'adj_open')
            if price == None:
                if noisy:
                    print "Price data unavailable for",ts,newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']
            else:
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                # profit = newOrder['shares'] * price - self.calcCommission(newOrder['shares']) # NEW
                if not (self.portfolio.hasStock(newOrder['symbol'],newOrder['shares'])): # NEW
                    #Not enough shares owned to sell requested amount
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = price #NEW
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                self.portfolio.sellTransaction(newOrder)
                #remove positions according to lifo/fifo
                self.position.removePosition(newOrder['symbol'],newOrder['shares'],newOrder['close_type'])
                #self.position.addPosition(ts,newOrder.symbol,newOrder.shares,price)
        elif newOrder['order_type'] == 'moc':
            #market order close
            price = strategyData.getPrice(ts, newOrder['symbol'], 'adj_close')
            if price == None:
                if noisy:
                    print "Price data unavailable for",ts,newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']        
            else:
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                #profit = newOrder['shares'] * price - self.calcCommission(newOrder['shares'])
                if not(self.portfolio.hasStock(newOrder['symbol'],newOrder['shares'])):
                    #Not enough shares owned to sell requested amount
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = price
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                self.portfolio.sellTransaction(newOrder)
                #remove positions according to lifo/fifo
                self.position.removePosition(newOrder['symbol'],newOrder['shares'],newOrder['close_type'])            
                #self.position.addPosition(ts,newOrder.symbol,newOrder.shares,price)
        elif newOrder['order_type'] == 'limit':
            #limit order
            price = newOrder['limit_price']
            if price == None:
                if noisy:
                    print "Price data unavailable for",ts,newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']
            else:
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                #profit = newOrder['shares'] * price - self.calcCommission(newOrder['shares'])
                if ((newOrder['limit_price'] > strategyData.getPrice(ts, newOrder['symbol'], 'adj_high')) or ( newOrder['limit_price'] < strategyData.getPrice(ts, newOrder['symbol'], 'adj_low'))):
                    #limit price outside of daily range
                    return None
                if not(self.portfolio.hasStock(newOrder['symbol'],newOrder['shares'])):
                    #Not enough shares owned to sell requested amount
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = price
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                self.portfolio.sellTransaction(newOrder)
                #remove positions according to lifo/fifo
                self.position.removePosition(newOrder['symbol'],newOrder['shares'],newOrder['close_type'])
                #self.position.addPosition(ts,newOrder.symbol,newOrder.shares,price)
        elif newOrder.order_type == 'vwap':
            #volume weighted average price
            price = strategyData.getPrice(ts, newOrder['symbol'], 'adj_open')
            if price == None:
                if noisy:
                    print "Price data unavailable for",ts,newOrder['symbol']
            if maxVol4Day == None:
                if noisy:
                    print "Volume Data Not Available for ts:", ts, 'stock:', newOrder['symbol']
            else:
                if newOrder['shares'] > maxVol4Day:
                    newOrder['shares'] = maxVol4Day
                    newOrder.update()
                    self.order.order.flush()
                price += strategyData.getPrice(ts, newOrder['symbol'], 'adj_close')
                price += strategyData.getPrice(ts, newOrder['symbol'], 'adj_high')
                price += strategyData.getPrice(ts, newOrder['symbol'], 'adj_low')
                price = price / 4.
                #profit = newOrder['shares'] * price - self.calcCommission(newOrder['shares'])
                if not (self.portfolio.hasStock(newOrder['symbol'],newOrder['shares'])):
                    #Not enough shares owned to sell requested amount
                    return None
                #__execute trade__
                #populate fill field in order
                newOrder['fill/timestamp'] = ts
                newOrder['fill/quantity'] = newOrder['shares']
                newOrder['fill/cashChange'] = price
                newOrder['fill/commission'] = self.calcCommission(newOrder['shares'])
                newOrder['fill/impactCost'] = newOrder['shares'] * price * self.calcEffect(maxVol4Day, newOrder['shares']) # This is the CHANGE in the total cost - what effect the volume has
                #add trade to portfolio
                self.portfolio.sellTransaction(newOrder)
                #remove positions according to lifo/fifo
                self.position.removePosition(newOrder['symbol'],newOrder['shares'],newOrder['close_type'])            
                #self.position.addPosition(ts,newOrder.symbol,newOrder.shares,price)
        else:
            #throw invalid type error
            raise TypeError("Not an existing trade type '%s'." % str(newOrder.order_type))
        newOrder.update()
        self.order.order.flush()
        return price
            
    def execute(self):
        count = 0
        for order in self.order.order.iterrows():
            #print 'ORDER:',order
            #print "order time of expiration:", order['duration'] + order['timestamp']
            #print "currTimestamp:", self.currTimestamp
            if (order['timestamp'] < self.currTimestamp):
                if (order['duration'] + order['timestamp']) >= self.currTimestamp:
                    #print order['fill']
                    if order['fill/timestamp'] == 0:
                        #Have unfilled, valid orders
                        if order['close_type'].upper() == "NONE":
                            #is a buy
                            result = self.buyStock(order)
                            if noisy:
                                if result:
                                    print "Succeeded in buying %d shares of %s for %.2f as %s, with close type %s. Placed at: %d.  Current timestamp: %d, order #%d" % (order['shares'], order['symbol'], result, order['order_type'], order['close_type'], order['timestamp'], self.currTimestamp, count)
                                else:
                                    print "Did not succeed in buying %d shares of %s as %s.  Order valid until %d. Placed at: %d.  Current timestamp: %d, order #%d" %(order['shares'], order['symbol'], order['order_type'], order['duration'] + order['timestamp'], order['timestamp'], self.currTimestamp, count)
                        else:
                            result = self.sellStock(order)
                            if noisy:
                                if result:
                                    print "Succeeded in selling %d shares of %s for %.2f as %s, with close type %s.  Current timestamp: %d" % (order['shares'], order['symbol'], result, order['order_type'], order['close_type'], self.currTimestamp)
                                else:
                                    print "Did not succeed in selling %d shares of %s as %s.  Order valid until %d.  Current timestamp: %d" %(order['shares'], order['symbol'], order['order_type'], order['duration'] + order['timestamp'], self.currTimestamp)
            count += 1
        
        
    def addOrders(self,commands):
        # commands format: ([(sale details),(sale details),...],[(purchase details),(purchase details),...])
        # sale details: (shares,symbol,orderType,duration,closeType,(optional) limit price)
        # purchase details: (shares,symbol,orderType,duration,closeType,(optional) limit price)
        for sellStock in commands[0]:
            if len(sellStock) == 6:
                newOrder = self.order.addOrder(self.getExecutionTimestamp(),sellStock[0],sellStock[1],sellStock[2],sellStock[3],sellStock[4],sellStock[5])
            else:
                newOrder = self.order.addOrder(self.getExecutionTimestamp(),sellStock[0],sellStock[1],sellStock[2],sellStock[3],sellStock[4])            
            newOrder.append()
            self.order.order.flush()
            """result = self.sellStock(newOrder)
            if noisy:
                if result:
                    print "Succeeded in selling %d shares of %s for %f as %s, with close type %s.  Current timestamp: %d" % (sellStock[0],sellStock[1],result,sellStock[2],sellStock[4],self.currTimestamp)
                else:
                    print "Did not succeed in selling %d shares of %s as %s.  Order valid until %d.  Current timestamp: %d" %(sellStock[0],sellStock[1],sellStock[2],sellStock[3]+self.currTimestamp,self.currTimestamp)
            """
            
        for buyStock in commands[1]:
            if len(buyStock) == 6:
                newOrder = self.order.addOrder(self.getExecutionTimestamp(),buyStock[0],buyStock[1],buyStock[2],buyStock[3],buyStock[4],buyStock[5])
            else:
                newOrder = self.order.addOrder(self.getExecutionTimestamp(),buyStock[0],buyStock[1],buyStock[2],buyStock[3],buyStock[4])            
            newOrder.append()
            self.order.order.flush()
            #print 'NEWORDER:',newOrder
            """result = self.buyStock(newOrder)
            if noisy:
                if result:
                    print "Succeeded in buying %d shares of %s for %f as %s, with close type %s.  Current timestamp: %d" % (buyStock[0],buyStock[1],result,buyStock[2],buyStock[4],self.currTimestamp)
                else:
                    print "Did not succeed in buying %d shares of %s as %s.  Order valid until %d.  Current timestamp: %d" %(buyStock[0],buyStock[1],buyStock[2],buyStock[3]+self.currTimestamp,self.currTimestamp)
            """        #print newOrder
                                  
    def run(self):
        if timersActive:
            print "Simulation timer started."
            totalTime = time.time()
            cycTime = time.clock()
        self.currTimestamp = self.startTime
        i=1
        while self.currTimestamp < self.endTime and self.currTimestamp < time.time() and self.currTimestamp < self.strategyData.timestampIndex[len(self.strategyData.timestampIndex)-2]:
            self.execute()
            self.addOrders(self.strategy(self.portfolio,self.currTimestamp,self.strategyData))
            if timersActive and not noisy:
                print "Strategy at %i took %.4f secs"%(self.currTimestamp,(time.clock()-cycTime))
                i+=1
                cycTime = time.clock()
            if noisy and not timersActive:
                print "\nStrategy at %d completed successfully." % self.currTimestamp
                print "Current portfolio value: %.2f."%self.portfolio.currCash
                print "Current stocks: %s.\n\n"%self.portfolio.currStocks
            if noisy and timersActive:
                print "\nStrategy at %i took %.4f secs"%(self.currTimestamp,(time.clock()-cycTime))
                print "Strategy at %d completed successfully." % self.currTimestamp
                print "Current portfolio value: %.2f."%self.portfolio.currCash
                print "Current stocks: %s.\n\n"%self.portfolio.currStocks
                i+=1
                cycTime = time.clock()  
            
            self.currTimestamp += self.interval
        if noisy:
            print "Simulation complete."
        if timersActive:
            print "Simulation complete in %i seconds."%(time.time() - totalTime)
        self.portfolio.close()
        self.position.close()
        self.order.close()
        if isTable:
            self.strategyData.close()



cash = 0; comPerShare = 0.0; minCom = 0.; startTime = 0; endTime = 0; timeStep = 0; maxEffect = 0.; decayCycles = 0
noisy = False; timersActive = False; isTable = False
def main():
    global cash,comPerShare,minCom,startTime,endTime,timeStep,maxEffect,decayCycles,noisy,timersActive, isTable
    # NOTE: the OptionParser class is currently not necessary, as we can just access sys.argv[1:], but if we
    # want to implement optional arguments, this will make it considerably easier.
    parser = OptionParser()
    
    # parser.parse_args() returns a tuple of (options, args)
    # As of right now, we don't have any options for our program, so we only care about the three arguments:
    # config file, strategy module name, strategy main function name
    args = parser.parse_args()[1]
    
    if len(args) != 3 and len(args) != 2:
        print "FAILURE TO INCLUDE THE CORRECT NUMBER OF ARGUMENTS; TERMINATING."
        return
    
    configFile = args[0]
    if len(args) == 3:
        stratName = args[2]
    else:
        stratName = "strategyMain"
    #print sys.path
    open(configFile,'r')
    for fileName in ["default.ini",configFile]:
        thisFile = open(fileName,'r')
        for line in thisFile.readlines():
            # Separate the command in the config file from the arguments
            if not ('#' in line):
                line = line.strip().split('=')
                command = line[0].strip().upper()
                if len(line)>1:
                    vals = line[1].upper().split()
                else:
                    vals = []
                # Parse commands, look for correct number of arguments, do rudimentary error checking, apply to simulator as appropriate
                if command == 'CASH':
                    if len(vals) != 1:
                        print "WRONG NUMBER OF ARGUMENTS FOR CASH!"
                    else:
                        try:
                            cash = float(vals[0])
                        except ValueError:
                            print "ARGUMENT FOR CASH IS NOT A FLOAT!"
                
                # Code for handling stocks in a starting portfolio.  Implementation not correct; removing for the time being.
#                elif command == "STOCK":
#                    if len(vals) != 2:
#                        print "WRONG NUMBER OF ARGUMENTS FOR STOCK!!  RAAAAWR!  ALSO, I NEED TO LEARN TO THROW ERRORS!"
#                    else:
#                        try:
#                            stocks.append([vals[0],int(vals[1])])
#                        except:
#                            print "STOCK TAKES IN A STOCK NAME AND AN INT!  AND DON'T YOU FORGET IT!"
                elif command == "COMPERSHARE":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR COMMISSIONS PER SHARE."
                    else:
                        try:
                            comPerShare = float(vals[0])
                        except ValueError:
                            print "COMMISSIONS PER SHARE REQUIRES A FLOAT INPUT"
                elif command == "MINCOM":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR MINIMUM COMMISSION."
                    else:
                        try:
                            minCom = float(vals[0])
                        except ValueError:
                            print "MINIMUM COMMISSIONS REQUIRES A FLOAT INPUT"
                elif command == "STARTTIME":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR START TIME."
                    else:
                        try:
                            startTime = long(vals[0])
                        except ValueError:
                            print "START TIME REQUIRES A LONG INPUT"
                elif command == "ENDTIME":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR END TIME."
                    else:
                        try:
                            endTime = long(vals[0])
                        except ValueError:
                            print "END TIME REQUIRES A LONG INPUT"
                elif command == "TIMESTEP":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR TIME STEP."
                    else:
                        try:
                            timeStep = long(vals[0])
                        except ValueError:
                            print "TIME STEP REQUIRES A LONG INPUT"
                elif command == "MAXMARKETEFFECT":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR MAX MARKET EFFECT."
                    else:
                        try:
                            maxEffect = float(vals[0])
                        except ValueError:
                            print "MAX MARKET EFFECT REQUIRES A FLOAT INPUT"
                elif command == "DECAYCYCLES":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR DECAY CYCLES."
                    else:
                        try:
                            decayCycles = int(vals[0])
                        except ValueError:
                            print "DECAY CYCLES REQUIRES AN INTEGER INPUT"
                elif command == "DATATYPE":
                    if len(vals) != 1:
                        print "NEED EXACTLY ONE PARAMETER FOR DATATYPE."
                    else:
                        if vals[0] == "TABLE":
                            isTable = True
                        elif vals[0] == "ARRAY":
                            isTable = False
                        else:
                            print "%s IS NOT A VALID PARAMETER FOR DATATYPE." % vals[0]  
                        print "I am using a table: ", isTable
                elif command == "NOISY":
                    noisy = True
                elif command == "TIMER":
                    timersActive = True
                elif command != '':
                        print "Unrecognized command '%s'.  Note: some commands may not yet be implemented.  E-mail pdohogne3@gatech.edu if a command is missing." % command
        thisFile.close()
    if noisy:
        print "Config file parsed successfully.  Starting simulation."
    
    
    # Add the strategies subdirectory to the system path so Python can find the module
    sys.path.append(sys.path[0] + '/strategies')
    myStrategy = eval("__import__('%s').%s" % (args[1],stratName) )
    
    mySim = Simulator(cash,{}, myStrategy, startTime, endTime, timeStep, minCom, comPerShare, isTable, maxEffect)
    # Add the timestamps
    if isTable:
        mySim.times = mySim.addTimeStamps()
    else:
        mySim.times = mySim.strategyData.timestampIndex
    #self.strategyData.populateArray(mySim.times)
    mySim.run()

# This ensures the main function runs automatically when the program is run from the command line, but 
# not if the file somehow gets imported from something else.  Nifty, eh?
if __name__ == "__main__":
    main()