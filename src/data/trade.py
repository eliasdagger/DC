import duckdb as dd
from pydantic import BaseModel
from typing import Literal
from datetime import date

conn = dd.connect("portfolio.duckdb")

class Transaction(BaseModel):
    client_id: int
    account: str
    Date: date
    action: Literal["buy", "sell"]
    tckr: str
    price: float
    quantity: float
    currency: Literal["USD", "CAD"]

def create_trades_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio(
            client_id INTEGER NOT NULL,
            account VARCHAR NOT NULL,
            date DATE NOT NULL,
            action VARCHAR NOT NULL CHECK (action IN ('buy', 'sell')),
            tckr VARCHAR NOT NULL,
            price DECIMAL(18,4) NOT NULL CHECK (price > 0), 
            quantity DECIMAL(24,10) NOT NULL CHECK (quantity > 0),
            currency VARCHAR NOT NULL CHECK (currency IN ('USD', 'CAD'))
        )
        """)
    
def trade(conn, t: Transaction):
    clients_conn = dd.connect('clients.duckdb')

    if clients_conn.execute("SELECT 1 FROM clients WHERE id = ?", [t.client_id]).fetchone() is None:
        raise ValueError(f"Client ID: {t.client_id} is not in clients.duckdb")
    name = clients_conn.execute("SELECT name FROM clients WHERE id = ?", [t.client_id]).fetchone()[0]

    if t.Date > date.today():
        raise ValueError(f"{t.Date} is in the future.")

    
    conn.execute(
        "INSERT INTO portfolio VALUES (?,?,?,?,?,?,?,?)",
        [t.client_id, t.account, t.Date, t.action, t.tckr, t.price, t.quantity, t.currency]
    )

    print(f"Successfully {"bought" if t.action == "buy" else "sold"} {t.quantity} of {t.tckr} @ {t.price}")

def show_trades(conn, client_id=None):
    if client_id is None:
        trades = conn.execute("SELECT * FROM portfolio ORDER BY date").df()
    else:
        trades = conn.execute("SELECT * FROM portfolio WHERE client_id = ? ORDER BY date", [client_id]).df()

    if trades.empty:
        print("No trades found.")
        return

    print(trades.to_string(index=False))

if __name__ == "__main__":
    conn = dd.connect("portfolio.duckdb")
    t = Transaction(client_id=1, account="TFSA", Date=date.today(), action="buy", tckr="AMZN", price=100, quantity=30, currency="USD")
    clients_conn = dd.connect("clients.duckdb")
    create_trades_table(conn)
    trade(conn, t)
    show_trades(conn)


