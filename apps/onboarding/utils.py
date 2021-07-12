#save json datafield of Bt table
def save_jsonfield_from_bu_prefsform(bt, buprefsform, tocreate):
    for k,v in bt.bu_preferences.items():
        if tocreate:
            if k in ('isvendor','isserviceprovider'):
                bt.bu_preferences[k] = buprefsform.cleaned_data[k]


#returns Bt json form
def get_bu_prefform(bt):
    from .forms import BuPrefForm
    d = {}
    for k, v in bt.bu_preferences.items():
        if k in ('isvendor','isserviceprovider'):
            d[k] = v
    return BuPrefForm(data=d)