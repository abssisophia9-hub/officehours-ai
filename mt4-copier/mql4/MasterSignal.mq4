//+------------------------------------------------------------------+
//| MasterSignal.mq4                                                 |
//| Local MT4 trade copier, master side.                             |
//| Writes open orders into Common Files\MT4Copier. No DLLs.         |
//| Does not read or store the account password.                     |
//+------------------------------------------------------------------+
#property copyright "Local MT4 trade copier"
#property strict
#property description "Publishes this terminal's open orders for the local copier."

input int    MagicFilter = 0;    // 0 copies every order. Otherwise only this magic.
input int    PollMs      = 200;  // Snapshot interval in milliseconds.
input string CommentTag  = "";   // Label stored in the snapshot. Not a password.

string OrderTypeName(int type)
{
   if(type == OP_BUY)       return "BUY";
   if(type == OP_SELL)      return "SELL";
   if(type == OP_BUYLIMIT)  return "BUYLIMIT";
   if(type == OP_SELLLIMIT) return "SELLLIMIT";
   if(type == OP_BUYSTOP)   return "BUYSTOP";
   if(type == OP_SELLSTOP)  return "SELLSTOP";
   return "UNKNOWN";
}

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
      else if(ch == '\t') out += "\\t";
      else                out += CharToString((uchar)ch);
   }
   return out;
}

bool EnsureFolder()
{
   if(!FolderCreate("MT4Copier", FILE_COMMON))
   {
      if(!FileIsExist("MT4Copier", FILE_COMMON) && GetLastError() != 0)
      {
         // FolderCreate returns false when the folder already exists on some builds.
      }
   }
   return true;
}

bool WriteAtomic(string finalName, string contents)
{
   string tmp = finalName + ".tmp";
   int handle = FileOpen(tmp, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(handle == INVALID_HANDLE)
   {
      Print("MasterSignal: cannot open ", tmp, " error ", GetLastError());
      return false;
   }
   FileWriteString(handle, contents);
   FileClose(handle);
   if(FileIsExist(finalName, FILE_COMMON))
      FileDelete(finalName, FILE_COMMON);
   if(!FileMove(tmp, FILE_COMMON, finalName, FILE_REWRITE|FILE_COMMON))
   {
      Print("MasterSignal: FileMove failed for ", finalName, " error ", GetLastError());
      return false;
   }
   return true;
}

string BuildSnapshot(int &exported)
{
   exported = 0;
   string orders = "[";
   bool first = true;
   int total = OrdersTotal();
   int index = 0;
   for(index = 0; index < total; index++)
   {
      if(!OrderSelect(index, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(MagicFilter != 0 && OrderMagicNumber() != MagicFilter)
         continue;
      if(!first)
         orders += ",";
      first = false;
      exported++;
      orders += "{\"ticket\":" + IntegerToString(OrderTicket());
      orders += ",\"symbol\":\"" + JsonEscape(OrderSymbol()) + "\"";
      orders += ",\"type\":\"" + OrderTypeName(OrderType()) + "\"";
      orders += ",\"lots\":" + DoubleToString(OrderLots(), 8);
      orders += ",\"open_price\":" + DoubleToString(OrderOpenPrice(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS));
      orders += ",\"sl\":" + DoubleToString(OrderStopLoss(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS));
      orders += ",\"tp\":" + DoubleToString(OrderTakeProfit(), (int)MarketInfo(OrderSymbol(), MODE_DIGITS));
      orders += ",\"comment\":\"" + JsonEscape(OrderComment()) + "\"";
      orders += ",\"magic\":" + IntegerToString(OrderMagicNumber());
      orders += ",\"open_time\":\"" + JsonEscape(TimeToString(OrderOpenTime(), TIME_DATE|TIME_SECONDS)) + "\"}";
   }
   orders += "]";

   string now = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   string account = IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   string body = "{\"time\":\"" + JsonEscape(now) + "\"";
   body += ",\"account\":" + account;
   body += ",\"comment_tag\":\"" + JsonEscape(CommentTag) + "\"";
   body += ",\"orders\":" + orders + "}";
   return body;
}

string BuildStatus(int exported)
{
   string now = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   bool allowed = TerminalInfoInteger(TERMINAL_CONNECTED) != 0;
   string body = "{\"time\":\"" + JsonEscape(now) + "\"";
   body += ",\"account\":" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   body += ",\"balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2);
   body += ",\"equity\":" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2);
   body += ",\"order_count\":" + IntegerToString(exported);
   body += ",\"comment_tag\":\"" + JsonEscape(CommentTag) + "\"";
   body += ",\"trade_allowed\":";
   body += (allowed ? "true" : "false");
   body += "}";
   return body;
}

void Publish()
{
   int exported = 0;
   string snapshot = BuildSnapshot(exported);
   string status = BuildStatus(exported);
   bool okSnap = WriteAtomic("MT4Copier\\master_snapshot.json", snapshot);
   bool okStat = WriteAtomic("MT4Copier\\master_status.json", status);
   string line = "MasterSignal\naccount " + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   line += "\norders " + IntegerToString(exported);
   line += "\nfolder: Common Files / MT4Copier";
   if(!okSnap || !okStat)
      line += "\nlast write failed, see Experts log";
   Comment(line);
}

int OnInit()
{
   EnsureFolder();
   int wait = PollMs;
   if(wait < 100)
      wait = 100;
   if(!EventSetMillisecondTimer(wait))
   {
      Print("MasterSignal: could not start the timer");
      return INIT_FAILED;
   }
   Print("MasterSignal: writing Common Files\\MT4Copier every ", wait, " ms. MagicFilter=", MagicFilter);
   Publish();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

void OnTimer()
{
   Publish();
}
