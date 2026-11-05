"""Wallet checkpoints measure net balance, never pretend to measure gross loot."""
def balance(value):
    if isinstance(value,bool):raise ValueError('Enter a whole mesos balance')
    text=str(value).strip().replace(',','')
    if not text.isascii() or not text.isdigit():raise ValueError('Enter a whole mesos balance')
    result=int(text)
    if not 0<=result<=2147483647:raise ValueError('Check mesos balance')
    return result

def checkpoint(session,current,initial=None):
    current=balance(current)
    if initial is None:
        initial=session.get('wallet_start')
        if initial is None:raise ValueError('Set starting wallet balance first')
    initial=balance(initial)
    result=dict(session)
    net=session.get('wallet_offset',0)+current-initial
    result.update(money_mode='wallet',wallet_start=initial,wallet_current=current,
                  wallet_net=net,mesos=net)
    return result
