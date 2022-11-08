def strip_punctuation_ru(s):
    punctuations = '''!()—[]{};:'"\,<>./?@#$%^&*_~'''

    new_s = ""
    for char in s:
        if char in punctuations:
            new_s += ' '
        else:
            new_s += char

    # заменим все последовательности вида " - " на " "
    new_s = new_s.replace(" - ", " ")
    return " ".join(new_s.split())


test_data = (('вид-нев', 'вид-нев'),
             ('много,разной.пунктуации!', 'много разной пунктуации'),
             ('вид - нев', 'вид нев'))
for inp, cor in test_data:
    out = strip_punctuation_ru(inp)
    if out != cor:
        print('NO')
        break
else:
    print('YES')