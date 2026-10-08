import csv,sys
for c in sys.argv[1:]:
    print('#####',c)
    for r in csv.DictReader(open(f'data/rows/{c}.csv')):
        print(r['no'],r['answer'],r['kokushi'] or r['origin'],r['src_flag'],'|',r['comment'].replace('\n',''))
