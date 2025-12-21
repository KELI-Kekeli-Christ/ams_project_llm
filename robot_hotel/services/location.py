from datetime import datetime

def get_heure_date():
    now = datetime.now()
    return f"Il est {now.strftime('%H:%M')} le {now.strftime('%d %B %Y')}."