# Local MT4 trade copier

This copies trades from one MetaTrader 4 terminal (the account a manager trades) into other MT4 terminals on the **same Windows PC**. Nothing is hosted. The app does not ask for a password, and it cannot withdraw or move money.

An account number by itself cannot place a trade. Each subscriber terminal must already be logged in to the broker with the trading password. The copier only reads and writes files that those terminals already have access to.

## What you need

- Windows PC
- MetaTrader 4, logged into the managed (master) account
- One more MT4 terminal for each subscriber account, already logged in
- Python 3 from [python.org](https://www.python.org/downloads/). During setup, check **Add python.exe to PATH**. No extra Python packages are required.

## 1. Install the Expert Advisors

1. On the **master** terminal, click **File → Open Data Folder**.
2. Open `MQL4\Experts`.
3. Copy `MasterSignal.mq4` from this folder's `mql4` directory into `Experts`.
4. Open **MetaEditor** (F4 in MT4), open `MasterSignal.mq4`, and press **Compile**. The bottom pane should say `0 error(s)`.
5. In MT4, turn on the **AutoTrading** button in the toolbar.
6. Open any chart. In Navigator → Expert Advisors, drag **MasterSignal** onto the chart.
7. In the dialog, enable **Allow live trading**. You can leave MagicFilter at `0` to publish every open order. Press OK.
8. A smiley face in the top-right of the chart means the EA is running. The chart comment should show the account and order count.

Do the same for each subscriber terminal, but copy and compile **SlaveCopier.mq4** instead. Give every subscriber a different **SlaveId** (letters, numbers, underscore, or hyphen), for example `alex-mt4`. That id must match what you type in the app later.

The slave EA's **MagicNumber** (default `880021`) is stamped on copied orders so you can tell them apart from manual trades. Slippage is in points. **MaxSpreadPoints** of `0` means "do not skip because of spread". Set it if you want the slave to skip a market open when the spread is wider than that many points.

## 2. One terminal per account

MT4 holds one login per terminal. For each subscriber:

1. Make a separate copy of the MT4 install folder.
2. Start it with portable mode so it does not kick the other login off:

   `terminal.exe /portable`

3. Log in with the **trading password** and the **broker server**. The account number alone is not enough.
4. Attach **SlaveCopier** with that account's SlaveId, AutoTrading on, and **Allow live trading** checked.

You only connect an account when the owner has asked you to trade it.

## 3. Check the Common Files folder

The terminals talk through files, not through a server. In **each** terminal click **File → Open Common Data Folder**, then open `Files`. After MasterSignal is running you should see:

`Files\MT4Copier\master_status.json`

Do this on a subscriber terminal too. Both windows must be the **same folder**. That is normal when every terminal runs as the same Windows user. If a portable copy opens a different Common folder, the copier cannot see it. Use a normal install under the same Windows user, or only use portable copies that share that Common folder.

The app's default folder is:

`%APPDATA%\MetaQuotes\Terminal\Common\Files\MT4Copier`

If Open Common Data Folder shows a different path, set `MT4_COPIER_DIR` to the `MT4Copier` folder (the one that contains `master_status.json`) before you start the app. You can uncomment the `set` line in `start.bat` and paste the path there.

## 4. Start the app

Double-click `start.bat`.

When the window says the UI is up, open:

http://127.0.0.1:8765

The page stays on this computer. It does not listen for other machines.

1. Check the master heartbeat (account, balance, equity, order count). If it says there is no heartbeat, MasterSignal is not writing the Common folder the app is reading. Compare the path on the page with Open Common Data Folder.
2. Add a subscriber: display name, the same SlaveId you typed on the EA, lot mode, and symbol settings.
3. A new subscriber is **off**. Open its card and tick **I am authorized to trade this account.**
4. Then tick **Enabled** and press Save.
5. The log lists every command sent and every fill the slave reports (ok or the error text).

**Lot mode**

- Multiplier: subscriber lots = master lots × multiplier, then fit to the broker minimum, step, and your max lot.
- Fixed lot: every new trade uses the fixed size, still capped by the max lot.

The slave EA also rounds volume to the broker minimum, maximum, and step it reads from the server. Prefix and suffix are added only when a command was not already mapped. Prefer the symbol map in the app (`GOLD=XAUUSD`, one pair per line). The app is the source of truth for symbol names.

**Pause** stops new copies. Trades the manager opens while you are paused are not copied later.

**Kill switch** stops new copies until you press Resume. It does not close trades that are already open, and it does not withdraw money.

Removing a subscriber also leaves their open trades alone. Close those in MT4 yourself if you need to.

## Try it without MT4

In a command prompt opened in this folder:

```
python -m app --simulate
```

That writes a fake master (open, move the stop loss, partial close, full close) and a fake subscriber that acknowledges each command. The page at http://127.0.0.1:8765 shows the same log. Those files stay under `data\simulate-bus` and do not go into a live MT4 folder unless you set `MT4_COPIER_DIR` yourself.

```
python -m app --simulate --once
```

prints the command list and exits. You should see `OPEN MODIFY PARTIAL CLOSE` and `simulate ok`.

## Limits

- MetaTrader 4 is Windows software. The Expert Advisors run only in MT4. This environment cannot compile them in MetaEditor or place a live order, so a real terminal is still required to confirm OrderSend, fills, and the Common Files path on your PC.
- Copy speed is the poll interval. The EAs default to 200 ms and the app checks about that often, so a copy is usually under a second and is not instant.
- The subscriber fills at **their** price. Fast markets can slip or reject (off quotes, requote, invalid stops, not enough money, market closed). The slave logs the plain reason and writes it to the fill file. Trade context busy is retried. A market-closed command stays at the front of that subscriber's queue until the market is open.
- Stop loss and take profit are copied as prices. If they are too close to the subscriber's price, the broker rejects the order.
- Trades **already open** on the master when you first start the app are not copied. They become the baseline, so a restart does not open them a second time. Trades the manager opens after that are copied. A restart remembers which master ticket already became which slave ticket.
- This does not withdraw, transfer, or hide trades. Copied orders are normal MT4 orders. The account owner can see them in the terminal.
- Only enable a subscriber whose owner asked you to trade that account.

## Files

```
mt4-copier/
  start.bat                 double-click to open the local page
  README.md                 these steps
  app/                      Python copier (standard library only)
  mql4/MasterSignal.mq4     attach on the managed account
  mql4/SlaveCopier.mq4      attach on each subscriber account
  tests/test_copier.py      unittest suite
  data/                     subscriber list and copier memory (created on the PC)
```

On the Common Files bus:

```
MT4Copier/master_snapshot.json      full list of master orders
MT4Copier/master_status.json        heartbeat
MT4Copier/control.json              pause / kill switch
MT4Copier/commands/<SlaveId>.jsonl  orders for that subscriber
MT4Copier/fills/<SlaveId>.jsonl     what the slave did
MT4Copier/config/<SlaveId>.json     enabled flag, lot cap, symbol prefix/suffix
MT4Copier/state/<SlaveId>.cursor    so commands are not repeated
MT4Copier/state/<SlaveId>.map       master ticket to slave ticket
```

To run the tests (optional):

```
cd mt4-copier
python -m unittest discover -s tests -v
python -m py_compile app\__init__.py app\__main__.py app\main.py app\bridge.py app\commands.py app\diff.py app\engine.py app\lots.py app\server.py app\simulator.py app\store.py app\symbols.py
```
