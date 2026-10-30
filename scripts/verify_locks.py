import hashlib,sys,os
ok=bad=miss=0
for l in open("out/r4m_audit/LOCK_HASHES.txt"):
    l=l.rstrip("\n")
    if not l or l.startswith("#"): continue
    h,_,p=l.partition("  ")
    if not os.path.exists(p): miss+=1; print("MISSING",p); continue
    if hashlib.sha256(open(p,"rb").read()).hexdigest()==h: ok+=1
    else: bad+=1; print("MISMATCH",p)
print(f"entries ok={ok} mismatch={bad} missing={miss}")
