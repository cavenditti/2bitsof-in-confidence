#!/usr/bin/env bash
# entropy_gzip.sh — live demo: compression ratio tracks entropy.
# bits/char = compressed_bytes * 8 / original_chars   (the empirical entropy estimate)
set -eu # NOT pipefail: 'tr | head' relies on SIGPIPE to stop tr

bpc() { # $1=label  $2=file
  local o c
  o=$(wc -c <"$2")
  c=$(gzip -9 -c "$2" | wc -c)
  awk -v l="$1" -v o="$o" -v c="$c" \
    'BEGIN{printf "%-26s %8dB raw  %7dB gz  %7.2fx  %6.3f bits/char\n", l, o, c, o/c, c*8/o}'
}

echo "============ A. PREDICTABLE  (theory: 0 bits/char) ============"
printf 'A%.0s' $(seq 100000) >a.txt
bpc "'A' x 100000" a.txt
echo "  -> structure is free. The only cost is gzip's fixed header."

echo
echo "============ B. RANDOM  (theory: log2(95) = 6.57 bits/char) ============"
LC_ALL=C tr -dc '[:print:]' </dev/urandom | head -c 100000 >b.txt
bpc "uniform printable ASCII" b.txt
echo "  -> gzip OVERSHOOTS 6.57 (it expands incompressible data)."
echo "     Compression is a one-sided bound: you approach H from above, never below."

echo
echo "============ C. ENGLISH  (Shannon floor: ~1.0 bits/char) ============"
if [ ! -s english.txt ]; then
  curl -fsSL "https://raw.githubusercontent.com/GITenberg/Pride-and-Prejudice_1342/master/1342.txt" |
    python3 -c 'import sys;t=sys.stdin.read();s=t.find("*** START");s=t.find("\n",s)+1 if s>=0 else 0;e=t.find("*** END");print(t[s:e if e>=0 else len(t)].strip())' \
      >english.txt
fi
for tool in "gzip -9" "bzip2 -9" "xz -9"; do
  o=$(wc -c <english.txt)
  c=$($tool -c english.txt | wc -c)
  awk -v t="$tool" -v o="$o" -v c="$c" 'BEGIN{printf "%-26s %8dB raw  %7dB  %6.3f bits/char\n", t, o, c, c*8/o}'
done
echo "  -> ~2-3 bits/char. NO general-purpose coder reaches 1.0."
echo "     The best LLMs hit ~0.9 (slide 31) because they are better PREDICTORS."

echo
echo "============ D. THE LEARNING CURVE  (more data -> closer to the floor) ============"
for n in 1000 10000 100000 600000; do
  head -c "$n" english.txt >seg.txt
  o=$(wc -c <seg.txt)
  c=$(bzip2 -9 -c seg.txt | wc -c)
  awk -v o="$o" -v c="$c" 'BEGIN{printf "  %8dB English  ->  %5.2f bits/char (bzip2)\n", o, c*8/o}'
done
echo "  -> the compressor 'trains' on the source. Cold start ~5 bits, warm ~2."
echo "     Same shape as a loss curve. Compression IS learning."

echo
echo "============ E. OVERHEAD TRAP  (don't measure tiny inputs) ============"
printf 'A%.0s' $(seq 10) >tiny.txt
bpc "'A' x 10 (predictable!)" tiny.txt
echo "  -> ratio < 1: gzip's ~18-byte header dominates. Entropy is asymptotic."
