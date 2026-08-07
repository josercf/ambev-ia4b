#!/bin/zsh
# Abre o deck do Módulo 2 servido localmente (duplo clique neste arquivo).
# Servir via http evita qualquer diferença de comportamento do file://.
cd "$(dirname "$0")"
PORTA=8931
if ! lsof -i :$PORTA >/dev/null 2>&1; then
  (python3 -m http.server $PORTA >/dev/null 2>&1 &)
  sleep 1
fi
open "http://localhost:$PORTA/aulas/modulo2.html"
