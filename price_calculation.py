async def get_insurance_price() -> int:
    '''
    in future there will be price calculation logic
    '''

    price = {
        "osago": 100
    }

    return price


async def get_insurance_price_all() -> dict:
    prices = {
        "osago": 100,
        "kasko": 200
    }
    return prices
