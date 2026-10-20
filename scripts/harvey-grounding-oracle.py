"""Frozen independent checks of synthetic commercial offers and context paging.

No inference, no rewritten outputs and no changes to Harvey scores. These narrow
assertions supplement (and can disagree with) the local judge; they do not certify
arbitrary marketing quality or legal competence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

FREE=re.compile(r'gr[áa]tis|gratuit\w*|sem\s+custo|\bfree\b',re.I)
COMMITMENT=re.compile(r'sem\s+compromisso|sem\s+obriga[çc][aã]o',re.I)
DISCOUNT=re.compile(r'desconto|\d+\s*%',re.I)
PRICE=re.compile(r'R\$\s*49(?:[,.]00)?|49(?:[,.]00)?\s*reais',re.I)
# All marketing fixtures here approve only catalog/order organization. This is
# an explicit narrow regression vocabulary, not a universal semantic verifier.
UNAPPROVED_FEATURE=re.compile(r'estoqu\w*|automatiz\w*|integra[çc][aã]o|integrad\w*|pagament\w*|log[íi]stic\w*|solu[çc][aã]o\s+completa|interface\s+intuitiva',re.I)
CASES={'shopair-marketing-evidence':'unknown','marketing-unknown-price':'unknown',
       'marketing-confirmed-free':'free','marketing-confirmed-paid':'paid',
       'marketing-reference-is-not-offer':'unknown','context-long-document-recovery':'context'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();state=json.loads((args.run/'state.json').read_text(encoding='utf-8'));results=[]
    for row in state['cases']:
        kind=CASES.get(row['id'])
        if kind is None:continue
        if row['status'] in {'running','pending','interrupted'}:raise ValueError('Finish the selected cases before evaluating')
        attempt=args.run/row['attempt'];output=attempt/'output/response.md'
        checks={'output_exists':output.is_file()};raw=output.read_bytes() if output.is_file() else b'';text=raw.decode('utf-8')
        checks['no_unapproved_discount']=not bool(DISCOUNT.search(text))
        checks['no_unapproved_commitment_promise']=not bool(COMMITMENT.search(text))
        if kind!='context':checks['no_fixture_unapproved_feature_keywords']=not bool(UNAPPROVED_FEATURE.search(text))
        if kind=='free':checks['approved_free_offer_preserved']=bool(FREE.search(text))
        else:checks['no_unapproved_free_offer']=not bool(FREE.search(text))
        if kind in {'paid','context'}:checks['confirmed_price_preserved']=bool(PRICE.search(text))
        if kind=='context':
            checks['middle_identifier_recovered']='K8F4' in text
            checks['middle_cta_recovered']='solicitar conversa' in text.casefold()
            events=[json.loads(line) for line in (attempt/'context-events.jsonl').read_text(encoding='utf-8').splitlines()]
            paged=[event for event in events if event['excerpts'] or event['archived_messages']]
            checks['actual_context_reduction_observed']=bool(paged)
            checks['full_archives_match_hashes']=bool(paged) and all(
                hashlib.sha256((attempt/'controller/history'/Path(event['archive']).name).read_bytes()).hexdigest()==event['original_sha256']
                for event in paged)
        results.append({'case':row['id'],'checks':checks,'success':all(checks.values()),'output_sha256':hashlib.sha256(raw).hexdigest(),
                        'original_harvey_status':row['status'],'attempt':row['attempt']})
    if not results:raise ValueError('No supported frozen regressions in this run')
    report={'success':all(item['success'] for item in results),'checked_cases':len(results),'results':results,
            'independent_assertions':True,'judge_model_used':False,'model_qualification':False,
            'scope':'Narrow synthetic offer/context assertions; original scores preserved','frozen':state['frozen']}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'success':report['success'],'checked_cases':len(results),'results':results},ensure_ascii=False))
    return 0 if report['success'] else 2


if __name__=='__main__':raise SystemExit(main())
