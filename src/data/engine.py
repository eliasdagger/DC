import duckdb as dd
import pandas as pd



conn = dd.connect('dagher.duckdb')


client
# create_clients_table(conn)
# add_client(conn, c1)
# print(get_client_data(conn, c1).to_string())

holdings
# create_holdings_table(conn)
# add_holdings(conn, stocks)
# print(conn.execute("SELECT * FROM holdings").df().to_string())

ingestion
if __name__ == "__main__":
    conn = dd.connect('dagher.duckdb')
    
    prices_amzn = get_prices("AMZN", "2024-01-01", "2024-12-31")
    print(prices_amzn.head())
    
    cache_prices(conn, prices_amzn, "AMZN")
    print("Cached.")

    conn.close()


returns
# annualized_return(conn, 'AMZN', "2024-01-01", "2024-12-31")

models
s = [Stock(ticker="AMZN", shares="10", purchase_price=12.0, purchase_date=date(2024, 1, 1)),
     Stock(ticker="MSFT", shares="12", purchase_price=10, purchase_date=date(2024, 1, 1))]

c1 = Client(id=123, name="John", risk_tolerance="High", holdings=s, goals="retirement")
print(c1)
