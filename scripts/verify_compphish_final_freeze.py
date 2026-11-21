#!/usr/bin/env python3
"""Verify frozen PoC inputs without reading final labels or predictions."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def main():
    freeze=json.loads((ROOT/'data/manifests/compphish_v4_final_freeze.json').read_text())
    if freeze['final_evaluation_run'] is not False or freeze['budget']!={'changed_coordinates':1,'total_binary_queries':5}:
        raise ValueError('Unexpected final status or budget')
    for name,item in freeze['artifacts'].items():
        path=ROOT/item['path']
        if not path.exists() or sha256(path)!=item['sha256']:
            raise ValueError(f'Frozen artifact differs: {name}')
    method=json.loads((ROOT/'data/manifests/compphish_v4_method_validation.json').read_text())
    if not method['method_validation_passed'] or method['final_split_evaluated']:
        raise ValueError('Method-validation or final status changed')
    print(f"Freeze verified: {len(freeze['artifacts'])} artifact hashes; final evaluation has not run.")
if __name__=='__main__':main()
