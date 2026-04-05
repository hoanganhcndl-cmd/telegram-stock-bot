def filter_data(rows, symbol):
    results = []
    if not rows or len(rows) < 2:
        return []

    symbol = symbol.upper()

    for r in rows[1:]:
        if len(r) < 5:
            continue

        db_ticker = str(r[0]).strip().upper()

        # ❌ Bỏ toàn bộ mã có hậu tố _NN
        if db_ticker.endswith("_NN"):
            continue

        # ✔ Chỉ lấy mã khớp chính xác
        if db_ticker == symbol:
            price = r[4]  # cột "Giá"
            date = r[1]
            results.append(f"🔹 {db_ticker} | {date} | Giá: {price}")

    return results[-10:]
