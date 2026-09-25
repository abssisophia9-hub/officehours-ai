//+------------------------------------------------------------------+
//| SlaveCopier.mq4                                                  |
//| Local MT4 trade copier, subscriber side.                         |
//| Places ordinary orders this terminal is already logged in to.    |
//| Does not read or store the account password. No DLLs.            |
//+------------------------------------------------------------------+
#property copyright "Local MT4 trade copier"
#property strict
#property description "Copies commands from Common Files\\MT4Copier for one SlaveId."

input string SlaveId          = "slave1"; // Must match the slave id in the local app.
input int    PollMs           = 200;      // How often to read new commands, in milliseconds.
input int    Slippage         = 3;        // Slippage in points for market orders.
input int    MaxSpreadPoints  = 0;        // 0 off. Skip a market open when the spread is wider.
input int    MagicNumber      = 880021;   // Magic stamped on copied orders.
input string SymbolPrefix     = "";       // Used only if the command was not already mapped.
input string SymbolSuffix     = "";       // Used only if the command was not already mapped.

int    gSlippage = 3;
int    gMaxSpread = 0;
int    gMagic = 880021;
string gPrefix = "";
string gSuffix = "";
double gMaxLot = 0;
bool   gEnabled = true;
string gLastNote = "";
int    gCursor = 0;
int    gMasterKeys[];
int    gSlaveVals[];

string JsonEscape(string value)
{
   string out = "";
   int length = StringLen(value);
   int index = 0;
   for(index = 0; index < length; index++)
   {
      int ch = StringGetChar(value, index);
      if(ch == '"')       out += "\\\"";
      else if(ch == '\\') out += "\\\\";
      else if(ch == '\n') out += "\\n";
      else if(ch == '\r') out += "\\r";
      else                out += CharToString((uchar)ch);
   }
   return out;
}

void Note(string text)
{
   Comment("SlaveCopier " + SlaveId + "\n" + text);
   if(text == gLastNote)
      return;
   gLastNote = text;
   Print("SlaveCopier ", SlaveId, ": ", text);
}

bool EnsureFolders()
{
   FolderCreate("MT4Copier", FILE_COMMON);
   FolderCreate("MT4Copier\\commands", FILE_COMMON);
   FolderCreate("MT4Copier\\fills", FILE_COMMON);
   FolderCreate("MT4Copier\\config", FILE_COMMON);
   FolderCreate("MT4Copier\\state", FILE_COMMON);
   return true;
}

string ReadText(string name)
{
   int handle = FileOpen(name, FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(handle == INVALID_HANDLE)
      return "";
   string data = "";
   while(!FileIsEnding(handle))
   {
      string line = FileReadString(handle);
      if(StringLen(data) > 0)
         data += "\n";
      data += line;
   }
   FileClose(handle);
   return data;
}

bool WriteAtomic(string finalName, string contents)
{
   string tmp = finalName + ".tmp";
   int handle = FileOpen(tmp, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(handle == INVALID_HANDLE)
      return false;
   FileWriteString(handle, contents);
   FileClose(handle);
   if(FileIsExist(finalName, FILE_COMMON))
      FileDelete(finalName, FILE_COMMON);
   return FileMove(tmp, FILE_COMMON, finalName, FILE_REWRITE|FILE_COMMON);
}

string JsonRaw(string json, string key)
{
   string pattern = "\"" + key + "\"";
   int found = StringFind(json, pattern, 0);
   if(found < 0)
      return "";
   int index = found + StringLen(pattern);
   int length = StringLen(json);
   while(index < length)
   {
      int ch = StringGetChar(json, index);
      if(ch != ' ' && ch != '\t')
         break;
      index++;
   }
   if(index >= length || StringGetChar(json, index) != ':')
      return "";
   index++;
   while(index < length)
   {
      int ch = StringGetChar(json, index);
      if(ch != ' ' && ch != '\t')
         break;
      index++;
   }
   if(index >= length)
      return "";
   if(StringGetChar(json, index) == '"')
   {
      index++;
      string value = "";
      while(index < length)
      {
         int ch = StringGetChar(json, index);
         if(ch == '\\')
         {
            index++;
            if(index >= length)
               break;
            int esc = StringGetChar(json, index);
            if(esc == '"' || esc == '\\' || esc == '/')
               value += CharToString((uchar)esc);
            else if(esc == 'n')
               value += "\n";
            else
               value += CharToString((uchar)esc);
            index++;
            continue;
         }
         if(ch == '"')
            break;
         value += CharToString((uchar)ch);
         index++;
      }
      return value;
   }
   int start = index;
   while(index < length)
   {
      int ch = StringGetChar(json, index);
      if(ch == ',' || ch == '}' || ch == ' ' || ch == '\n' || ch == '\r')
         break;
      index++;
   }
   return StringSubstr(json, start, index - start);
}

double JsonNumber(string json, string key)
{
   string raw = JsonRaw(json, key);
   if(raw == "" || raw == "null")
      return 0;
   return StringToDouble(raw);
}

bool JsonBool(string json, string key)
{
   return JsonRaw(json, key) == "true";
}

bool HasKey(string json, string key)
{
   return StringFind(json, "\"" + key + "\"", 0) >= 0;
}

void LoadConfig()
{
   gSlippage = Slippage;
   gMaxSpread = MaxSpreadPoints;
   gMagic = MagicNumber;
   gPrefix = SymbolPrefix;
   gSuffix = SymbolSuffix;
   gMaxLot = 0;
   gEnabled = true;
   string path = "MT4Copier\\config\\" + SlaveId + ".json";
   if(!FileIsExist(path, FILE_COMMON))
      return;
   string text = ReadText(path);
   if(StringLen(text) == 0)
      return;
   if(HasKey(text, "enabled"))
      gEnabled = JsonBool(text, "enabled");
   if(HasKey(text, "max_lot"))
      gMaxLot = JsonNumber(text, "max_lot");
   if(HasKey(text, "symbol_prefix"))
      gPrefix = JsonRaw(text, "symbol_prefix");
   if(HasKey(text, "symbol_suffix"))
      gSuffix = JsonRaw(text, "symbol_suffix");
}

bool Halted()
{
   string path = "MT4Copier\\control.json";
   if(!FileIsExist(path, FILE_COMMON))
      return false;
   string text = ReadText(path);
   if(JsonBool(text, "killed") || JsonBool(text, "paused"))
      return true;
   return false;
}

bool TradingOn()
{
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) == 0)
      return false;
   if(MQLInfoInteger(MQL_TRADE_ALLOWED) == 0)
      return false;
   return true;
}

string CursorPath()
{
   return "MT4Copier\\state\\" + SlaveId + ".cursor";
}

string MapPath()
{
   return "MT4Copier\\state\\" + SlaveId + ".map";
}

string FillPath()
{
   return "MT4Copier\\fills\\" + SlaveId + ".jsonl";
}

string CommandPath()
{
   return "MT4Copier\\commands\\" + SlaveId + ".jsonl";
}

void LoadCursor()
{
   gCursor = 0;
   if(!FileIsExist(CursorPath(), FILE_COMMON))
      return;
   string text = ReadText(CursorPath());
   StringTrimLeft(text);
   StringTrimRight(text);
   gCursor = (int)StringToInteger(text);
   if(gCursor < 0)
      gCursor = 0;
}

void SaveCursor()
{
   WriteAtomic(CursorPath(), IntegerToString(gCursor));
}

void LoadMap()
{
   ArrayResize(gMasterKeys, 0);
   ArrayResize(gSlaveVals, 0);
   if(!FileIsExist(MapPath(), FILE_COMMON))
      return;
   string text = ReadText(MapPath());
   string parts[];
   int count = StringSplit(text, '\n', parts);
   int index = 0;
   for(index = 0; index < count; index++)
   {
      string line = parts[index];
      StringTrimLeft(line);
      StringTrimRight(line);
      int comma = StringFind(line, ",", 0);
      if(comma <= 0)
         continue;
      int master = (int)StringToInteger(StringSubstr(line, 0, comma));
      int slave = (int)StringToInteger(StringSubstr(line, comma + 1));
      if(master <= 0 || slave <= 0)
         continue;
      int size = ArraySize(gMasterKeys);
      ArrayResize(gMasterKeys, size + 1);
      ArrayResize(gSlaveVals, size + 1);
      gMasterKeys[size] = master;
      gSlaveVals[size] = slave;
   }
}

void SaveMap()
{
   string body = "";
   int index = 0;
   int size = ArraySize(gMasterKeys);
   for(index = 0; index < size; index++)
   {
      body += IntegerToString(gMasterKeys[index]) + "," + IntegerToString(gSlaveVals[index]) + "\n";
   }
   WriteAtomic(MapPath(), body);
}

int MapGet(int master)
{
   int index = 0;
   int size = ArraySize(gMasterKeys);
   for(index = 0; index < size; index++)
   {
      if(gMasterKeys[index] == master)
         return gSlaveVals[index];
   }
   return -1;
}

void MapPut(int master, int slave)
{
   int index = 0;
   int size = ArraySize(gMasterKeys);
   for(index = 0; index < size; index++)
   {
      if(gMasterKeys[index] == master)
      {
         gSlaveVals[index] = slave;
         SaveMap();
         return;
      }
   }
   ArrayResize(gMasterKeys, size + 1);
   ArrayResize(gSlaveVals, size + 1);
   gMasterKeys[size] = master;
   gSlaveVals[size] = slave;
   SaveMap();
}

string Marker(int master)
{
   string text = "c" + IntegerToString(master);
   if(StringLen(text) > 31)
      text = StringSubstr(text, 0, 31);
   return text;
}

int FindSlaveTicket(int master)
{
   int mapped = MapGet(master);
   if(mapped > 0 && OrderSelect(mapped, SELECT_BY_TICKET, MODE_TRADES))
      return mapped;
   string marker = Marker(master);
   int total = OrdersTotal();
   int index = 0;
   for(index = total - 1; index >= 0; index--)
   {
      if(!OrderSelect(index, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(gMagic != 0 && OrderMagicNumber() != gMagic)
         continue;
      if(OrderComment() == marker)
      {
         MapPut(master, OrderTicket());
         return OrderTicket();
      }
   }
   return -1;
}

int TypeFromName(string name)
{
   if(name == "BUY") return OP_BUY;
   if(name == "SELL") return OP_SELL;
   if(name == "BUYLIMIT") return OP_BUYLIMIT;
   if(name == "SELLLIMIT") return OP_SELLLIMIT;
   if(name == "BUYSTOP") return OP_BUYSTOP;
   if(name == "SELLSTOP") return OP_SELLSTOP;
   return -1;
}

bool MarketOrder(int type)
{
   return type == OP_BUY || type == OP_SELL;
}

bool Tradable(string symbol)
{
   if(StringLen(symbol) == 0)
      return false;
   if(!SymbolSelect(symbol, true))
      return false;
   if(MarketInfo(symbol, MODE_POINT) <= 0)
      return false;
   return true;
}

string ResolveSymbol(string raw, bool mapped)
{
   string candidate = raw;
   if(!mapped)
      candidate = gPrefix + raw + gSuffix;
   if(Tradable(candidate))
      return candidate;
   return "";
}

double NormalizeVolume(string symbol, double lots, bool raiseToMin)
{
   double minLot = MarketInfo(symbol, MODE_MINLOT);
   double maxLot = MarketInfo(symbol, MODE_MAXLOT);
   double step = MarketInfo(symbol, MODE_LOTSTEP);
   if(step <= 0)
      step = 0.01;
   if(minLot <= 0)
      minLot = step;
   if(gMaxLot > 0 && gMaxLot < maxLot)
      maxLot = gMaxLot;
   if(lots <= 0)
      return 0;
   if(lots < minLot)
   {
      if(!raiseToMin)
         return 0;
      lots = minLot;
   }
   if(lots > maxLot)
      lots = maxLot;
   lots = MathFloor(lots / step + 0.5) * step;
   if(lots > maxLot)
      lots = MathFloor(maxLot / step) * step;
   if(lots < minLot)
   {
      if(!raiseToMin)
         return 0;
      lots = minLot;
   }
   int digits = 2;
   if(step < 0.009)
      digits = 3;
   if(step < 0.0009)
      digits = 4;
   return NormalizeDouble(lots, digits);
}

string PlainError(int code)
{
   if(code == ERR_TRADE_CONTEXT_BUSY || code == ERR_BROKER_BUSY || code == ERR_SERVER_BUSY)
      return "trade context busy: retry";
   if(code == ERR_MARKET_CLOSED)
      return "market closed";
   if(code == ERR_INVALID_TRADE_VOLUME)
      return "invalid volume";
   if(code == ERR_OFF_QUOTES)
      return "off quotes";
   if(code == ERR_REQUOTE || code == ERR_PRICE_CHANGED)
      return "requote";
   if(code == ERR_INVALID_STOPS)
      return "invalid stops";
   if(code == ERR_INVALID_PRICE)
      return "invalid price";
   if(code == ERR_NOT_ENOUGH_MONEY)
      return "not enough money";
   if(code == ERR_TRADE_DISABLED)
      return "trading disabled";
   return "error " + IntegerToString(code);
}

bool RetryLater(int code)
{
   if(code == ERR_TRADE_CONTEXT_BUSY) return true;
   if(code == ERR_SERVER_BUSY) return true;
   if(code == ERR_BROKER_BUSY) return true;
   if(code == ERR_OFF_QUOTES) return true;
   if(code == ERR_REQUOTE) return true;
   if(code == ERR_PRICE_CHANGED) return true;
   if(code == ERR_TRADE_TIMEOUT) return true;
   if(code == ERR_NO_CONNECTION) return true;
   if(code == ERR_MARKET_CLOSED) return true;
   return false;
}

void WriteFill(string commandId, bool ok, int slaveTicket, int master, string eventName, int errorCode, string message)
{
   string line = "{\"command_id\":\"" + JsonEscape(commandId) + "\"";
   line += ",\"ok\":";
   line += (ok ? "true" : "false");
   line += ",\"slave_ticket\":" + IntegerToString(slaveTicket);
   line += ",\"master_ticket\":" + IntegerToString(master);
   line += ",\"event\":\"" + JsonEscape(eventName) + "\"";
   line += ",\"error_code\":" + IntegerToString(errorCode);
   line += ",\"retcode\":" + IntegerToString(errorCode);
   line += ",\"message\":\"" + JsonEscape(message) + "\"";
   line += ",\"time\":\"" + JsonEscape(TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)) + "\"}\n";
   int handle = FileOpen(FillPath(), FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(handle == INVALID_HANDLE)
      handle = FileOpen(FillPath(), FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(handle == INVALID_HANDLE)
   {
      Note("could not write the fill file, error " + IntegerToString(GetLastError()));
      return;
   }
   FileSeek(handle, 0, SEEK_END);
   FileWriteString(handle, line);
   FileClose(handle);
}

double MarketPrice(string symbol, int type)
{
   RefreshRates();
   double price = (type == OP_BUY) ? MarketInfo(symbol, MODE_ASK) : MarketInfo(symbol, MODE_BID);
   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   return NormalizeDouble(price, digits);
}

bool SpreadOk(string symbol)
{
   if(gMaxSpread <= 0)
      return true;
   double spread = MarketInfo(symbol, MODE_SPREAD);
   return spread <= gMaxSpread;
}

// Returns 1 when the cursor should advance, 0 when the same command should be retried.
int ExecuteCommand(string line)
{
   string eventName = JsonRaw(line, "event");
   string commandId = JsonRaw(line, "id");
   int master = (int)JsonNumber(line, "master_ticket");
   bool mapped = JsonBool(line, "mapped");
   string symbol = ResolveSymbol(JsonRaw(line, "symbol"), mapped);
   int type = TypeFromName(JsonRaw(line, "type"));

   if(StringLen(commandId) == 0 || StringLen(eventName) == 0 || master <= 0)
   {
      Note("skipping a command with missing id, event, or ticket");
      return 1;
   }
   if(StringLen(symbol) == 0)
   {
      Note("unknown symbol " + JsonRaw(line, "symbol"));
      WriteFill(commandId, false, 0, master, eventName, 4106, "unknown symbol");
      return 1;
   }

   if(eventName == "OPEN")
   {
      int existing = FindSlaveTicket(master);
      if(existing > 0)
      {
         Note("master " + IntegerToString(master) + " is already ticket " + IntegerToString(existing));
         WriteFill(commandId, true, existing, master, eventName, 0, "already open");
         return 1;
      }
      if(type < 0)
      {
         Note("unknown order type");
         WriteFill(commandId, false, 0, master, eventName, ERR_INVALID_TRADE_PARAMETERS, "unknown order type");
         return 1;
      }
      if(MarketOrder(type) && !SpreadOk(symbol))
      {
         Note("spread too wide on " + symbol);
         WriteFill(commandId, false, 0, master, eventName, 0, "spread too wide");
         return 1;
      }
      double lots = NormalizeVolume(symbol, JsonNumber(line, "lots"), true);
      if(lots <= 0)
      {
         Note("invalid volume");
         WriteFill(commandId, false, 0, master, eventName, ERR_INVALID_TRADE_VOLUME, "invalid volume");
         return 1;
      }
      int digits = (int)MarketInfo(symbol, MODE_DIGITS);
      double price = JsonNumber(line, "price");
      if(MarketOrder(type))
         price = MarketPrice(symbol, type);
      else
         price = NormalizeDouble(price, digits);
      double sl = NormalizeDouble(JsonNumber(line, "sl"), digits);
      double tp = NormalizeDouble(JsonNumber(line, "tp"), digits);
      string comment = Marker(master);
      int ticket = -1;
      int errorCode = 0;
      int attempt = 0;
      for(attempt = 0; attempt < 5; attempt++)
      {
         RefreshRates();
         if(MarketOrder(type))
            price = MarketPrice(symbol, type);
         ResetLastError();
         ticket = OrderSend(symbol, type, lots, price, gSlippage, sl, tp, comment, gMagic, 0, clrNONE);
         if(ticket > 0)
            break;
         errorCode = GetLastError();
         if(!RetryLater(errorCode))
            break;
         Sleep(200);
      }
      if(ticket > 0)
      {
         MapPut(master, ticket);
         Note("opened master " + IntegerToString(master) + " as ticket " + IntegerToString(ticket));
         WriteFill(commandId, true, ticket, master, eventName, 0, "ok");
         return 1;
      }
      string reason = PlainError(errorCode);
      Note(reason);
      if(RetryLater(errorCode))
         return 0;
      WriteFill(commandId, false, 0, master, eventName, errorCode, reason);
      return 1;
   }

   int slaveTicket = FindSlaveTicket(master);
   if(slaveTicket <= 0)
   {
      Note("no slave ticket for master " + IntegerToString(master));
      WriteFill(commandId, false, 0, master, eventName, 4108, "no slave ticket for master ticket");
      return 1;
   }
   if(!OrderSelect(slaveTicket, SELECT_BY_TICKET, MODE_TRADES))
   {
      Note("slave order is not open");
      WriteFill(commandId, false, slaveTicket, master, eventName, 4108, "slave order is not open");
      return 1;
   }

   if(eventName == "MODIFY")
   {
      int digits = (int)MarketInfo(OrderSymbol(), MODE_DIGITS);
      double price = OrderOpenPrice();
      if(!MarketOrder(OrderType()))
         price = NormalizeDouble(JsonNumber(line, "price"), digits);
      double sl = NormalizeDouble(JsonNumber(line, "sl"), digits);
      double tp = NormalizeDouble(JsonNumber(line, "tp"), digits);
      ResetLastError();
      bool changed = OrderModify(slaveTicket, price, sl, tp, 0, clrNONE);
      int errorCode = GetLastError();
      if(changed || errorCode == ERR_NO_RESULT || errorCode == 0)
      {
         Note("modified ticket " + IntegerToString(slaveTicket));
         WriteFill(commandId, true, slaveTicket, master, eventName, 0, "ok");
         return 1;
      }
      string reason = PlainError(errorCode);
      Note(reason);
      if(RetryLater(errorCode))
         return 0;
      WriteFill(commandId, false, slaveTicket, master, eventName, errorCode, reason);
      return 1;
   }

   if(eventName == "PARTIAL" || eventName == "CLOSE")
   {
      int orderType = OrderType();
      string orderSymbol = OrderSymbol();
      double orderLots = OrderLots();
      if(!MarketOrder(orderType))
      {
         if(eventName == "PARTIAL")
         {
            Note("pending orders cannot be partially closed");
            WriteFill(commandId, false, slaveTicket, master, eventName, ERR_INVALID_TRADE_PARAMETERS, "pending orders cannot be partially closed");
            return 1;
         }
         ResetLastError();
         bool deleted = OrderDelete(slaveTicket, clrNONE);
         int errorCode = GetLastError();
         if(deleted)
         {
            Note("deleted pending ticket " + IntegerToString(slaveTicket));
            WriteFill(commandId, true, slaveTicket, master, eventName, 0, "ok");
            return 1;
         }
         string reason = PlainError(errorCode);
         Note(reason);
         if(RetryLater(errorCode))
            return 0;
         WriteFill(commandId, false, slaveTicket, master, eventName, errorCode, reason);
         return 1;
      }

      double closeLots = orderLots;
      if(eventName == "PARTIAL")
      {
         closeLots = JsonNumber(line, "close_lots");
         if(closeLots <= 0)
            closeLots = orderLots - JsonNumber(line, "lots");
         closeLots = NormalizeVolume(orderSymbol, closeLots, false);
         if(closeLots <= 0 || closeLots > orderLots + 0.0000001)
         {
            Note("invalid volume");
            WriteFill(commandId, false, slaveTicket, master, eventName, ERR_INVALID_TRADE_VOLUME, "invalid volume");
            return 1;
         }
      }
      double price = MarketPrice(orderSymbol, orderType == OP_BUY ? OP_SELL : OP_BUY);
      int errorCode = 0;
      bool closed = false;
      int attempt = 0;
      for(attempt = 0; attempt < 5; attempt++)
      {
         RefreshRates();
         price = MarketPrice(orderSymbol, orderType == OP_BUY ? OP_SELL : OP_BUY);
         ResetLastError();
         if(!OrderSelect(slaveTicket, SELECT_BY_TICKET, MODE_TRADES))
         {
            errorCode = GetLastError();
            break;
         }
         closed = OrderClose(slaveTicket, closeLots, price, gSlippage, clrNONE);
         if(closed)
            break;
         errorCode = GetLastError();
         if(!RetryLater(errorCode))
            break;
         Sleep(200);
      }
      if(closed)
      {
         Note(eventName + " ticket " + IntegerToString(slaveTicket));
         WriteFill(commandId, true, slaveTicket, master, eventName, 0, "ok");
         return 1;
      }
      string reason = PlainError(errorCode);
      Note(reason);
      if(RetryLater(errorCode))
         return 0;
      WriteFill(commandId, false, slaveTicket, master, eventName, errorCode, reason);
      return 1;
   }

   Note("unknown event " + eventName);
   WriteFill(commandId, false, 0, master, eventName, 0, "unknown event");
   return 1;
}

int ReadCommandLines(string &lines[])
{
   ArrayResize(lines, 0);
   if(!FileIsExist(CommandPath(), FILE_COMMON))
      return 0;
   int handle = FileOpen(CommandPath(), FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(handle == INVALID_HANDLE)
      return -1;
   int count = 0;
   while(!FileIsEnding(handle))
   {
      string line = FileReadString(handle);
      StringTrimLeft(line);
      StringTrimRight(line);
      ArrayResize(lines, count + 1);
      lines[count] = line;
      count++;
   }
   FileClose(handle);
   return count;
}

void ProcessCommands()
{
   LoadConfig();
   if(Halted() || !gEnabled)
   {
      Note("copying is paused or this subscriber is disabled");
      return;
   }
   if(!TradingOn())
   {
      Note("AutoTrading is off. Turn on AutoTrading and Allow live trading.");
      return;
   }
   string lines[];
   int count = ReadCommandLines(lines);
   if(count < 0)
   {
      Note("could not read the command file");
      return;
   }
   if(gCursor > count)
   {
      Note("command file is shorter than the saved cursor; not replaying old commands");
      return;
   }
   int index = gCursor;
   int stepped = 0;
   for(index = gCursor; index < count && stepped < 20; index++)
   {
      string line = lines[index];
      if(StringLen(line) == 0)
      {
         gCursor = index + 1;
         continue;
      }
      bool complete = (StringFind(line, "{", 0) >= 0 && StringFind(line, "}", 0) >= 0);
      if(!complete)
      {
         if(index == count - 1)
         {
            Note("waiting for a command line to finish writing");
            break;
         }
         Note("skipping a corrupt command line");
         gCursor = index + 1;
         continue;
      }
      int advance = ExecuteCommand(line);
      if(advance == 0)
         break;
      gCursor = index + 1;
      stepped++;
   }
   SaveCursor();
}

bool SlaveIdOk()
{
   int length = StringLen(SlaveId);
   if(length < 1 || length > 32)
      return false;
   int index = 0;
   for(index = 0; index < length; index++)
   {
      int ch = StringGetChar(SlaveId, index);
      bool letter = (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z');
      bool digit = (ch >= '0' && ch <= '9');
      if(!letter && !digit && ch != '_' && ch != '-')
         return false;
   }
   return true;
}

int OnInit()
{
   if(!SlaveIdOk())
   {
      Print("SlaveCopier: SlaveId must be 1-32 letters, numbers, underscores, or hyphens");
      return INIT_FAILED;
   }
   EnsureFolders();
   LoadCursor();
   LoadMap();
   int wait = PollMs;
   if(wait < 100)
      wait = 100;
   if(!EventSetMillisecondTimer(wait))
   {
      Print("SlaveCopier: could not start the timer");
      return INIT_FAILED;
   }
   Print("SlaveCopier: id ", SlaveId, " reading Common Files\\MT4Copier\\commands\\", SlaveId, ".jsonl");
   Note("attached. Waiting for commands.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

void OnTimer()
{
   ProcessCommands();
}
