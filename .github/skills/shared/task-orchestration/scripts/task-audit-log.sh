#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Generate deterministic full/short audit artifacts for task lifecycle events.
# Security:
#   Writes only under configured audits root; does not execute external payloads.

mode=""
task_id=""
role=""
action=""
status="ok"
session_id="${DIGITAL_SESSION_ID:-}"
audits_root=".digital-artifacts/70-audits"
date_key="$(date +%F)"
artifacts=""
assumptions=""
open_questions=""
status_summary=""
next_step_override=""
handoff_file=""
notes=""
message_id=""
execution_stack=""
skills_trace=""
agents_trace=""
instructions_trace=""
mcp_endpoints_trace=""
communication_flow=""
flow_svg_relpath=""
handoff_expected="auto"
timing_total_ms=""
timing_pre_hook_ms=""
timing_command_ms=""
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
runtime_handoff_root=""

resolve_runtime_handoff_root() {
  if [[ -n "${DIGITAL_RUNTIME_HANDOFF_ROOT:-}" ]]; then
    printf '%s' "$DIGITAL_RUNTIME_HANDOFF_ROOT"
    return 0
  fi

  if [[ "$audits_root" != ".digital-artifacts/70-audits" ]]; then
    local audits_parent
    audits_parent="$(cd "$(dirname "$audits_root")" && pwd)"
    printf '%s' "$audits_parent/.digital-runtime/handoffs/audit"
    return 0
  fi

  printf '%s' "$repo_root/.digital-runtime/handoffs/audit"
}

stage_handoff_file_for_runtime() {
  local source_path="${1:-}"
  local audit_date="${2:-}"
  local audit_code="${3:-}"

  if [[ -z "$source_path" || ! -f "$source_path" ]]; then
    printf '%s' "$source_path"
    return 0
  fi

  if [[ "$source_path" != /* ]]; then
    source_path="$PWD/$source_path"
  fi

  local target_dir="$runtime_handoff_root/$audit_date/$audit_code"
  mkdir -p "$target_dir"
  local target_file="$target_dir/$(basename "$source_path")"
  if [[ "$source_path" != "$target_file" ]]; then
    cp "$source_path" "$target_file"
  fi

  if [[ "$target_file" == "$repo_root/"* ]]; then
    printf '%s' "${target_file#$repo_root/}"
  else
    printf '%s' "$target_file"
  fi
}

trim_text() {
  local value="${1:-}"
  value="${value#${value%%[![:space:]]*}}"
  value="${value%${value##*[![:space:]]}}"
  printf '%s' "$value"
}

csv_count() {
  local csv="${1:-}"
  if [[ -z "$(trim_text "$csv")" ]]; then
    printf '0'
    return 0
  fi

  printf '%s' "$csv" | awk -F',' '
    {
      count = 0
      for (i = 1; i <= NF; i++) {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
        if ($i != "") {
          count++
        }
      }
      print count
    }
  '
}

artifact_group_key() {
  local artifact
  artifact="$(trim_text "${1:-}")"
  if [[ -z "$artifact" ]]; then
    printf 'uncategorized'
    return 0
  fi

  case "$artifact" in
    .digital-artifacts/*/*)
      printf '%s/%s' "${artifact%%/*}" "$(printf '%s' "$artifact" | cut -d'/' -f2)"
      ;;
    .digital-runtime/handoffs/*)
      printf '.digital-runtime/handoffs'
      ;;
    */*)
      printf '%s' "$(dirname "$artifact")"
      ;;
    *)
      printf '%s' "$artifact"
      ;;
  esac
}

has_handoff_protocol_marker() {
  local haystack="${1:-}"
  [[ "$haystack" == *"work_handoff_v1"* ]] && return 0
  [[ "$haystack" == *"expert_request_v1"* ]] && return 0
  [[ "$haystack" == *"expert_response_v1"* ]] && return 0
  return 1
}

handoff_protocol_from_content() {
  local haystack="${1:-}"
  if [[ "$haystack" == *"work_handoff_v1"* ]]; then
    printf 'work_handoff_v1'
  elif [[ "$haystack" == *"expert_request_v1"* ]]; then
    printf 'expert_request_v1'
  elif [[ "$haystack" == *"expert_response_v1"* ]]; then
    printf 'expert_response_v1'
  else
    printf 'unknown'
  fi
}

is_handoff_artifact_path() {
  local artifact
  artifact="$(trim_text "${1:-}")"
  case "$artifact" in
    *.yaml|*.yml)
      ;;
    *)
      return 1
      ;;
  esac

  case "$artifact" in
    .digital-runtime/handoffs/*|*/handoffs/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

resolve_repo_absolute_path() {
  local candidate
  candidate="$(trim_text "${1:-}")"
  if [[ -z "$candidate" ]]; then
    printf ''
    return 0
  fi
  if [[ "$candidate" == /* ]]; then
    printf '%s' "$candidate"
  else
    printf '%s' "$repo_root/$candidate"
  fi
}

handoff_pair_side() {
  local path
  path="$(trim_text "${1:-}")"
  case "$path" in
    *_REQUEST.yaml|*.expert_request.yaml)
      printf 'request'
      ;;
    *_RESPONSE.yaml|*.expert_response.yaml)
      printf 'response'
      ;;
    *)
      printf 'none'
      ;;
  esac
}

handoff_pair_key() {
  local path
  path="$(trim_text "${1:-}")"
  path="${path%.*}"
  path="${path%_REQUEST}"
  path="${path%_RESPONSE}"
  path="${path%.expert_request}"
  path="${path%.expert_response}"
  printf '%s' "$path"
}

render_handoff_snippets_markdown() {
  local artifacts_csv="${1:-}"
  local primary_handoff_file="${2:-}"
  local -a handoff_paths=()
  local -a artifact_array=()
  local artifact trimmed found_handoff existing_handoff

  IFS=',' read -r -a artifact_array <<<"$artifacts_csv"
  for artifact in "${artifact_array[@]:-}"; do
    trimmed="$(trim_text "$artifact")"
    [[ -n "$trimmed" ]] || continue
    if ! is_handoff_artifact_path "$trimmed"; then
      continue
    fi

    found_handoff="0"
    for existing_handoff in "${handoff_paths[@]:-}"; do
      if [[ "$existing_handoff" == "$trimmed" ]]; then
        found_handoff="1"
        break
      fi
    done
    if [[ "$found_handoff" == "0" ]]; then
      handoff_paths+=("$trimmed")
    fi
  done

  if [[ -n "$primary_handoff_file" ]] && is_handoff_artifact_path "$primary_handoff_file"; then
    found_handoff="0"
    for existing_handoff in "${handoff_paths[@]:-}"; do
      if [[ "$existing_handoff" == "$primary_handoff_file" ]]; then
        found_handoff="1"
        break
      fi
    done
    if [[ "$found_handoff" == "0" ]]; then
      handoff_paths+=("$primary_handoff_file")
    fi
  fi

  if [[ "${#handoff_paths[@]}" -eq 0 ]]; then
    return 0
  fi

  printf '### Handoff Snippets\n\n'
  printf 'Captured handoff request/response payload snippets for this run.\n\n'

  local pair_count=0
  local -a pair_keys=()
  local -a pair_requests=()
  local -a pair_responses=()
  local pair_side pair_key pair_found pair_index
  for handoff_path_item in "${handoff_paths[@]:-}"; do
    pair_side="$(handoff_pair_side "$handoff_path_item")"
    [[ "$pair_side" != "none" ]] || continue
    pair_key="$(handoff_pair_key "$handoff_path_item")"
    pair_found="0"
    for ((pair_index=0; pair_index<pair_count; pair_index++)); do
      if [[ "${pair_keys[$pair_index]}" == "$pair_key" ]]; then
        pair_found="1"
        if [[ "$pair_side" == "request" ]]; then
          pair_requests[$pair_index]="1"
        else
          pair_responses[$pair_index]="1"
        fi
        break
      fi
    done
    if [[ "$pair_found" == "0" ]]; then
      pair_keys[$pair_count]="$pair_key"
      if [[ "$pair_side" == "request" ]]; then
        pair_requests[$pair_count]="1"
        pair_responses[$pair_count]="0"
      else
        pair_requests[$pair_count]="0"
        pair_responses[$pair_count]="1"
      fi
      pair_count=$((pair_count + 1))
    fi
  done

  if [[ "$pair_count" -gt 0 ]]; then
    local complete_pairs=0
    local missing_response_pairs=0
    local missing_request_pairs=0
    for ((pair_index=0; pair_index<pair_count; pair_index++)); do
      if [[ "${pair_requests[$pair_index]}" == "1" && "${pair_responses[$pair_index]}" == "1" ]]; then
        complete_pairs=$((complete_pairs + 1))
      elif [[ "${pair_requests[$pair_index]}" == "1" ]]; then
        missing_response_pairs=$((missing_response_pairs + 1))
      else
        missing_request_pairs=$((missing_request_pairs + 1))
      fi
    done
    printf -- '- Pair status: %s complete, %s missing response, %s missing request.\n\n' "$complete_pairs" "$missing_response_pairs" "$missing_request_pairs"
  fi

  local handoff_snippet_max_lines=120
  local handoff_path_item handoff_abs handoff_content handoff_protocol_label
  local handoff_line_count handoff_truncated
  for handoff_path_item in "${handoff_paths[@]:-}"; do
    handoff_abs="$(resolve_repo_absolute_path "$handoff_path_item")"
    if [[ ! -f "$handoff_abs" ]]; then
      printf -- '- %s (missing at render time)\n' "$handoff_path_item"
      continue
    fi

    handoff_content="$(cat "$handoff_abs" 2>/dev/null || true)"
    handoff_protocol_label="$(handoff_protocol_from_content "$handoff_content")"
    handoff_line_count="$(printf '%s\n' "$handoff_content" | wc -l | tr -d ' ')"
    handoff_truncated="no"
    if [[ "$handoff_line_count" -gt "$handoff_snippet_max_lines" ]]; then
      handoff_content="$(printf '%s\n' "$handoff_content" | sed -n "1,${handoff_snippet_max_lines}p")"
      handoff_truncated="yes"
    fi

    printf '<details>\n'
    if [[ "$handoff_truncated" == "yes" ]]; then
      printf '<summary>%s: %s (truncated to %s lines)</summary>\n\n' "$handoff_protocol_label" "$handoff_path_item" "$handoff_snippet_max_lines"
    else
      printf '<summary>%s: %s</summary>\n\n' "$handoff_protocol_label" "$handoff_path_item"
    fi
    printf '```yaml\n'
    printf '%s\n' "$handoff_content"
    printf '```\n'
    printf '</details>\n\n'
  done
}

xml_escape() {
  local input="${1:-}"
  input="${input//&/&amp;}"
  input="${input//</&lt;}"
  input="${input//>/&gt;}"
  input="${input//\"/&quot;}"
  input="${input//\'/&apos;}"
  printf '%s' "$input"
}

html_unescape() {
  local input="${1:-}"
  printf '%s' "$input" | sed \
    -e 's/&amp;/\&/g' \
    -e 's/&lt;/</g' \
    -e 's/&gt;/>/g' \
    -e 's/&quot;/"/g' \
    -e "s/&apos;/'/g"
}

format_duration_ms() {
  local ms="${1:-}"
  [[ -z "$ms" ]] && printf 'n/a' && return
  if [[ "$ms" -ge 10000 ]]; then
    printf '%d s' "$((ms / 1000))"
  elif [[ "$ms" -ge 1000 ]]; then
    local whole=$((ms / 1000))
    local tenth=$(( (ms % 1000) / 100 ))
    printf '%d.%d s' "$whole" "$tenth"
  else
    printf '%d ms' "$ms"
  fi
}

format_duration_seconds() {
  local ms="${1:-}"
  [[ -z "$ms" ]] && printf 'n/a' && return
  LC_ALL=C awk -v value="$ms" 'BEGIN { printf "%.2f s", value / 1000 }'
}

render_sequence_svg() {
  local flow_text="${1:-}"
  local target_file="${2:-}"
  local summary_label="${3:-}"
  local total_duration="${4:-}"
  [[ -n "$flow_text" ]] || return 0
  [[ -n "$target_file" ]] || return 0
  local svg_content
  svg_content="$(printf '%s' "$flow_text" | LC_ALL=C awk \
    -v summary="$summary_label" \
    -v totalDuration="${total_duration:-}" \
    '
    function xe(s,   r){r=s;gsub(/&/,"\\&amp;",r);gsub(/</,"\\&lt;",r);gsub(/>/,"\\&gt;",r);gsub(/"/,"\\&quot;",r);return r}
    function tr2(s,  r){r=s;gsub(/^[[:space:]]+|[[:space:]]+$/,"",r);return r}
    function actorWrapped(nm,   s){s=nm;gsub(/[[:space:]]*\([^)]+\)/,"\\n&",s);gsub(/[[:space:]]*\//,"\\n/",s);gsub(/[[:space:]]+-/,"\\n-",s);gsub(/[[:space:]]+sub-agents/,"\\nsub-agents",s);gsub(/[[:space:]]+Orchestrator/,"\\nOrchestrator",s);gsub(/[[:space:]]+Prompt[[:space:]]+Alias/,"\\nPrompt Alias",s);gsub(/[[:space:]]+\(/,"\\n(",s);return s}
    function actorLineCount(nm,   wrapped,tmp,count){wrapped=actorWrapped(nm);tmp=wrapped;count=split(tmp, __tmp, /\\n/);return count>0?count:1}
    function actorTextSvg(centerX, centerY, rawLabel,   wrapped,lineCnt,lineHeight,startY,i,line){wrapped=actorWrapped(rawLabel);lineCnt=split(wrapped, __actorLines, /\\n/);lineHeight=13;startY=centerY-((lineCnt-1)*lineHeight/2)+4;out="  <text x=\""centerX"\" y=\""startY"\" fill=\"#bae6fd\" font-family=\"Menlo,Monaco,Consolas,monospace\" font-size=\"11\" text-anchor=\"middle\">";for(i=1;i<=lineCnt;i++){line=xe(tr2(__actorLines[i]));if(length(line)==0)continue;if(i==1)out=out "<tspan x=\""centerX"\" dy=\"0\">" line "</tspan>";else out=out "<tspan x=\""centerX"\" dy=\"13\">" line "</tspan>";}out=out "</text>";return out}
    function findA(nm, k){for(k=1;k<=actorCnt;k++){if(actors[k]==nm)return k}return 0}
    function addA(nm,  k){k=findA(nm);if(k==0){actorCnt++;actors[actorCnt]=nm;return actorCnt}return k}
    BEGIN{actorCnt=0;stepCnt=0}
    {
      n=split($0,SS,";")
      for(p=1;p<=n;p++){
        s=tr2(SS[p]);if(length(s)==0)next
        isDashed=0
        if(index(s,"-->")>0){isDashed=1;arrowPos=index(s,"-->");fromP=tr2(substr(s,1,arrowPos-1));restP=tr2(substr(s,arrowPos+3))}
        else if(index(s,"->")>0){arrowPos=index(s,"->");fromP=tr2(substr(s,1,arrowPos-1));restP=tr2(substr(s,arrowPos+2))}
        else next
        if(length(fromP)==0)next
        cp=index(restP,":")
        if(cp>0){toP=tr2(substr(restP,1,cp-1));lblP=tr2(substr(restP,cp+1))}
        else{toP=tr2(restP);lblP=""}
        if(length(toP)==0)next
        addA(fromP);addA(toP)
        stepCnt++;SF[stepCnt]=fromP;ST[stepCnt]=toP;SL[stepCnt]=lblP;SD[stepCnt]=isDashed
      }
    }
    END{
      if(stepCnt==0&&actorCnt==0)exit 0
      MX=80;AW=155;AH=38;TH=70;AT=TH+8;SH=64;BM=50;MINW=700
      maxActorLines=1
      for(i=1;i<=actorCnt;i++){lc=actorLineCount(actors[i]);if(lc>maxActorLines)maxActorLines=lc}
      if(maxActorLines>1) AH=AH+(maxActorLines-1)*13+6
      nw=actorCnt*190+140;W=(nw>MINW)?nw:MINW
      TOTALH=AT+AH+stepCnt*SH+BM
      if(actorCnt==1){acX[1]=W/2}
      else{sp=(W-2*MX)/(actorCnt-1);for(i=1;i<=actorCnt;i++){acX[i]=MX+(i-1)*sp}}
      LT=AT+AH;LB=TOTALH-BM+20
      print "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\""W"\" height=\""TOTALH"\" viewBox=\"0 0 "W" "TOTALH"\">"
      print "  <rect x=\"0\" y=\"0\" width=\""W"\" height=\""TOTALH"\" fill=\"#0b1220\"/>"
      print "  <rect x=\"18\" y=\"10\" width=\""(W-36)"\" height=\"50\" rx=\"10\" fill=\"#111827\" stroke=\"#334155\"/>"
      print "  <text x=\"36\" y=\"32\" fill=\"#e5e7eb\" font-family=\"Menlo,Monaco,Consolas,monospace\" font-size=\"15\" font-weight=\"bold\">Sequence Diagram</text>"
      if(length(summary)>0) print "  <text x=\"230\" y=\"32\" fill=\"#93c5fd\" font-family=\"Menlo,Monaco,Consolas,monospace\" font-size=\"12\">"xe(summary)"</text>"
      if(length(totalDuration)>0) print "  <text x=\"36\" y=\"52\" fill=\"#64748b\" font-family=\"Menlo,Monaco,Consolas,monospace\" font-size=\"11\">Runtime: "totalDuration"</text>"
      for(i=1;i<=actorCnt;i++){bx=acX[i]-AW/2;print "  <rect x=\""bx"\" y=\""AT"\" width=\""AW"\" height=\""AH"\" rx=\"5\" fill=\"#1e293b\" stroke=\"#38bdf8\" stroke-width=\"1.5\"/>"; print actorTextSvg(acX[i], AT+AH/2, actors[i])}
      for(i=1;i<=actorCnt;i++) print "  <line x1=\""acX[i]"\" y1=\""LT"\" x2=\""acX[i]"\" y2=\""LB"\" stroke=\"#334155\" stroke-width=\"1\" stroke-dasharray=\"6 4\"/>"
      for(j=1;j<=stepCnt;j++){
        fIdx=findA(SF[j]);tIdx=findA(ST[j])
        if(fIdx!=0&&tIdx!=0){
          cY=LT+SH*(j-0.5);lY=cY-8;aY=cY+8;fX=acX[fIdx];tX=acX[tIdx]
          print "  <text x=\"6\" y=\""(aY+4)"\" fill=\"#64748b\" font-family=\"Menlo,Monaco,Consolas,monospace\" font-size=\"10\">"j"</text>"
          safeL=xe(SL[j])
          if(fIdx==tIdx){
            loopX=fX+32
            print "  <path d=\"M"fX" "(aY-10)" L"loopX" "(aY-10)" L"loopX" "(aY+10)" L"(fX+12)" "(aY+10)"\" fill=\"none\" stroke=\"#f59e0b\" stroke-width=\"1.5\" marker-end=\"url(#arr_self)\"/>"
            if(length(safeL)>0) print "  <text x=\""(loopX+4)"\" y=\""lY"\" fill=\"#fcd34d\" font-family=\"Menlo,Monaco,Consolas,monospace\" font-size=\"11\">"safeL"</text>"
          }else{
            dr=(tX>fX)?1:-1;ax1=fX+dr*7;ax2=tX-dr*14;midX=(fX+tX)/2
            dashA=SD[j]?" stroke-dasharray=\"6 3\"":""
            arrowCol=SD[j]?"#94a3b8":"#38bdf8"
            mrkr=SD[j]?"arr_ret":"arr_fwd"
            print "  <line x1=\""ax1"\" y1=\""aY"\" x2=\""ax2"\" y2=\""aY"\" stroke=\""arrowCol"\" stroke-width=\"2\""dashA" marker-end=\"url(#"mrkr")\"/>"
            if(length(safeL)>0) print "  <text x=\""midX"\" y=\""lY"\" fill=\"#e2e8f0\" font-family=\"Menlo,Monaco,Consolas,monospace\" font-size=\"11\" text-anchor=\"middle\">"safeL"</text>"
          }
        }
      }
      print "  <defs>"
      print "    <marker id=\"arr_fwd\" markerWidth=\"8\" markerHeight=\"8\" refX=\"6\" refY=\"3\" orient=\"auto\"><path d=\"M0,0 L0,6 L6,3 z\" fill=\"#38bdf8\"/></marker>"
      print "    <marker id=\"arr_ret\" markerWidth=\"8\" markerHeight=\"8\" refX=\"6\" refY=\"3\" orient=\"auto\"><path d=\"M0,0 L0,6 L6,3 z\" fill=\"#94a3b8\"/></marker>"
      print "    <marker id=\"arr_self\" markerWidth=\"8\" markerHeight=\"8\" refX=\"3\" refY=\"3\" orient=\"auto\"><path d=\"M0,0 L0,6 L6,3 z\" fill=\"#f59e0b\" transform=\"rotate(-90 3 3)\"/></marker>"
      print "  </defs>"
      print "</svg>"
    }
    ')"
  if [[ -n "$svg_content" ]]; then
    printf '%s\n' "$svg_content" >"$target_file"
  fi
}

iso_timestamp_utc() {
  perl -MTime::HiRes=gettimeofday -MPOSIX=strftime -e '($s,$us)=gettimeofday; print strftime("%Y-%m-%dT%H:%M:%S", gmtime($s)).sprintf(".%03dZ", int($us/1000));'
}

resolve_audit_enabled() {
  if [[ -n "${DIGITAL_AUDIT_ENABLED:-}" ]]; then
    if [[ "${DIGITAL_AUDIT_ENABLED}" == "0" ]]; then
      echo "0"
      return 0
    fi
    echo "1"
    return 0
  fi

  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  local layer_id
  layer_id="${DIGITAL_LAYER_ID:-$(basename "$repo_root") }"
  layer_id="${layer_id% }"
  local state_file
  state_file="$repo_root/.digital-runtime/layers/$layer_id/audit/state.env"

  if [[ -f "$state_file" ]]; then
    local state_line
    state_line="$(grep -E '^DIGITAL_AUDIT_ENABLED=' "$state_file" 2>/dev/null || true)"
    if [[ "$state_line" == "DIGITAL_AUDIT_ENABLED=0" ]]; then
      echo "0"
      return 0
    fi
  fi

  echo "1"
}

next_audit_code_for_dir() {
  local target_dir="${1:-}"
  local last_code=""
  [[ -d "$target_dir" ]] || {
    printf '00000'
    return 0
  }

  last_code="$({ find "$target_dir" -maxdepth 1 -type f -name '*.audit.md' -print 2>/dev/null \
    | sed -E 's#.*/([0-9]{5})(-[^/]+)?\.audit\.md#\1#' | grep -E '^[0-9]{5}$' | sort | tail -n1; } || true)"
  if [[ -z "$last_code" ]]; then
    printf '00000'
    return 0
  fi
  local next_value=$((10#$last_code + 1))
  printf '%05d' "$next_value"
}

find_audit_file_for_message_id() {
  local search_root="${1:-}"
  local target_message_id="${2:-}"
  [[ -n "$search_root" && -d "$search_root" && -n "$target_message_id" ]] || return 0

  while IFS= read -r candidate; do
    if grep -Fq -- "- message_id: ${target_message_id}" "$candidate" 2>/dev/null; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done < <(find "$search_root" -maxdepth 2 -type f -name '*.audit.md' -print 2>/dev/null | sort)

  return 0
}

find_latest_audit_file_for_basename() {
  local target_dir="${1:-}"
  local target_basename="${2:-}"
  [[ -n "$target_dir" && -d "$target_dir" && -n "$target_basename" ]] || return 0

  local latest
  latest="$({
    find "$target_dir" -maxdepth 1 -type f -name "*-${target_basename}.audit.md" -print 2>/dev/null \
      | sort
  } || true)"
  latest="$(printf '%s\n' "$latest" | tail -n1)"
  [[ -n "$latest" ]] && printf '%s\n' "$latest"
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --task-id)
      task_id="${2:-}"
      shift 2
      ;;
    --role)
      role="${2:-}"
      shift 2
      ;;
    --action)
      action="${2:-}"
      shift 2
      ;;
    --status)
      status="${2:-ok}"
      shift 2
      ;;
    --session-id)
      session_id="${2:-}"
      shift 2
      ;;
    --audits-root)
      audits_root="${2:-}"
      shift 2
      ;;
    --date)
      date_key="${2:-}"
      shift 2
      ;;
    --artifacts)
      artifacts="${2:-}"
      shift 2
      ;;
    --assumptions)
      assumptions="${2:-}"
      shift 2
      ;;
    --open-questions)
      open_questions="${2:-}"
      shift 2
      ;;
    --status-summary)
      status_summary="${2:-}"
      shift 2
      ;;
    --next-step)
      next_step_override="${2:-}"
      shift 2
      ;;
    --handoff-file)
      handoff_file="${2:-}"
      shift 2
      ;;
    --notes)
      notes="${2:-}"
      shift 2
      ;;
    --message-id)
      message_id="${2:-}"
      shift 2
      ;;
    --execution-stack)
      execution_stack="${2:-}"
      shift 2
      ;;
    --skills-trace)
      skills_trace="${2:-}"
      shift 2
      ;;
    --agents-trace)
      agents_trace="${2:-}"
      shift 2
      ;;
    --instructions-trace)
      instructions_trace="${2:-}"
      shift 2
      ;;
    --mcp-endpoints-trace)
      mcp_endpoints_trace="${2:-}"
      shift 2
      ;;
    --communication-flow)
      communication_flow="${2:-}"
      shift 2
      ;;
    --handoff-expected)
      handoff_expected="${2:-auto}"
      shift 2
      ;;
    --timing-total-ms)
      timing_total_ms="${2:-}"
      shift 2
      ;;
    --timing-pre-hook-ms)
      timing_pre_hook_ms="${2:-}"
      shift 2
      ;;
    --timing-command-ms)
      timing_command_ms="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$mode" == "amend" ]]; then
  [[ -n "$message_id" ]] || { printf 'Error: --message-id is required for --mode amend\n' >&2; exit 2; }
  task_id="${task_id:-session-task}"
  role="${role:-copilot}"
  action="${action:-amend}"
else
  [[ "$mode" == "full" || "$mode" == "short" ]] || { printf 'Error: --mode must be full|short|amend\n' >&2; exit 2; }
  [[ -n "$task_id" ]] || { printf 'Error: --task-id is required\n' >&2; exit 2; }
  [[ -n "$role" ]] || { printf 'Error: --role is required\n' >&2; exit 2; }
  [[ -n "$action" ]] || { printf 'Error: --action is required\n' >&2; exit 2; }
fi

audit_enabled="$(resolve_audit_enabled)"
runtime_handoff_root="$(resolve_runtime_handoff_root)"
if [[ "$audit_enabled" != "1" ]]; then
  cat <<EOF
api_version: "v1"
kind: "task_audit_log"
status: "skipped"
mode: "${mode}"
task_id: "${task_id}"
role: "${role}"
action: "${action}"
audit_file: ""
EOF
  exit 0
fi

# ── AMEND MODE ───────────────────────────────────────────────────────────────
if [[ "$mode" == "amend" ]]; then
  amend_file="$(find_audit_file_for_message_id "$audits_root" "$message_id")"
  if [[ -z "$amend_file" ]]; then
    printf '[ERROR] No audit file found for message-id: %s\n' "$message_id" >&2
    exit 2
  fi
  amend_dir="$(dirname "$amend_file")"
  amend_code="${amend_file##*/}"
  amend_code="${amend_code%.audit.md}"
  amend_asset_dir="${amend_dir}/${amend_code}"
  mkdir -p "$amend_asset_dir"

  handoff_protocol="none"
  handoff_evidence="none"
  if [[ -n "$handoff_file" ]]; then
    if [[ ! -f "$handoff_file" ]]; then
      printf '[ERROR] handoff file not found: %s\n' "$handoff_file" >&2
      exit 2
    fi
    amend_date_key="$(basename "$amend_dir")"
    handoff_file="$(stage_handoff_file_for_runtime "$handoff_file" "$amend_date_key" "$amend_code")"
    handoff_evidence="handoff_file"
    if [[ "$handoff_file" != /* ]]; then
      _handoff_abs="$repo_root/$handoff_file"
    else
      _handoff_abs="$handoff_file"
    fi
    _hf_content="$(cat "$_handoff_abs" 2>/dev/null || true)"
    if [[ "$_hf_content" == *"work_handoff_v1"* ]]; then
      handoff_protocol="work_handoff_v1"
    elif [[ "$_hf_content" == *"expert_request_v1"* ]]; then
      handoff_protocol="expert_request_v1"
    elif [[ "$_hf_content" == *"expert_response_v1"* ]]; then
      handoff_protocol="expert_response_v1"
    fi
  elif [[ -n "$assumptions" || -n "$open_questions" ]]; then
    handoff_evidence="inline_fields"
  fi

  amend_ts="$(iso_timestamp_utc)"
  {
    printf '\n## Handoff Update\n\n'
    printf -- '- updated_at: %s\n' "$amend_ts"
    printf -- '- handoff_file: %s\n' "${handoff_file:-not_provided}"
    printf -- '- protocol: %s\n' "$handoff_protocol"
    printf -- '- evidence: %s\n' "$handoff_evidence"
    [[ -n "$assumptions" ]] && printf -- '- assumptions: %s\n' "$assumptions"
    [[ -n "$open_questions" ]] && printf -- '- open_questions: %s\n' "$open_questions"
    printf '\n'
  } >>"$amend_file"

  if [[ -n "$communication_flow" ]]; then
    amend_svg_relpath="${amend_code}/sequence-flow.svg"
    timing_total_seconds=""
    [[ -n "$timing_total_ms" ]] && timing_total_seconds="$(format_duration_seconds "$timing_total_ms")"
    render_sequence_svg "$communication_flow" "${amend_asset_dir}/sequence-flow.svg" "${summary_text:-}" "$timing_total_seconds"
  fi

  printf 'api_version: "v1"\n'
  printf 'kind: "task_audit_log"\n'
  printf 'status: "ok"\n'
  printf 'mode: "amend"\n'
  printf 'task_id: "%s"\n' "$task_id"
  printf 'role: "%s"\n' "$role"
  printf 'action: "amend"\n'
  printf 'audit_file: "%s"\n' "$amend_file"
  exit 0
fi
# ─────────────────────────────────────────────────────────────────────────────

if [[ -z "$session_id" ]]; then
  session_id="session-$(date +%Y%m%d-%H%M%S)"
fi

audit_dir="$audits_root/$date_key"
mkdir -p "$audit_dir"

audit_basename="$(trim_text "${DIGITAL_AUDIT_BASENAME:-}")"
if [[ -n "$audit_basename" ]]; then
  audit_basename="$(printf '%s' "$audit_basename" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//')"
fi

reuse_latest_for_basename="$(trim_text "${DIGITAL_AUDIT_REUSE_LATEST_FOR_BASENAME:-}")"
append_rerun_marker="no"
latest_for_basename=""
existing_for_message_id=""

next_code="$(next_audit_code_for_dir "$audit_dir")"
if [[ -n "$audit_basename" ]]; then
  audit_code="${next_code}-${audit_basename}"
else
  audit_code="$next_code"
fi

if [[ -n "$message_id" ]]; then
  existing_for_message_id="$(find_audit_file_for_message_id "$audit_dir" "$message_id")"
  if [[ -n "$existing_for_message_id" ]]; then
    audit_code="${existing_for_message_id##*/}"
    audit_code="${audit_code%.audit.md}"
  fi
fi

if [[ -z "$existing_for_message_id" && "$reuse_latest_for_basename" == "1" && -n "$audit_basename" ]]; then
  latest_for_basename="$(find_latest_audit_file_for_basename "$audit_dir" "$audit_basename")"
  if [[ -n "$latest_for_basename" ]]; then
    audit_code="${latest_for_basename##*/}"
    audit_code="${audit_code%.audit.md}"
    append_rerun_marker="yes"
  fi
fi

audit_file="$audit_dir/${audit_code}.audit.md"
audit_asset_dir="$audit_dir/${audit_code}"
mkdir -p "$audit_asset_dir"
timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
timestamp_utc="$(iso_timestamp_utc)"

if [[ ! -f "$audit_file" ]]; then
  {
    printf '# Task Audit\n\n'
    printf -- '- task_id: %s\n' "$task_id"
    printf -- '- role: %s\n' "$role"
    printf -- '- session_id: %s\n' "$session_id"
    if [[ -n "$message_id" ]]; then
      printf -- '- message_id: %s\n' "$message_id"
    fi
    printf '\n'
  } >"$audit_file"
fi

actor_count="$(csv_count "$agents_trace")"

handoff_protocol="none"
if has_handoff_protocol_marker "$notes"; then
  if [[ "$notes" == *"work_handoff_v1"* ]]; then
    handoff_protocol="work_handoff_v1"
  elif [[ "$notes" == *"expert_request_v1"* ]]; then
    handoff_protocol="expert_request_v1"
  elif [[ "$notes" == *"expert_response_v1"* ]]; then
    handoff_protocol="expert_response_v1"
  fi
fi

handoff_evidence="none"
if [[ -n "$handoff_file" ]]; then
  if [[ -f "$handoff_file" ]]; then
    handoff_file="$(stage_handoff_file_for_runtime "$handoff_file" "$date_key" "$audit_code")"
  fi
fi
# Detect handoff protocol from file content when file is provided
if [[ -n "$handoff_file" && "$handoff_protocol" == "none" ]]; then
  if [[ "$handoff_file" != /* ]]; then
    _handoff_abs="$repo_root/$handoff_file"
  else
    _handoff_abs="$handoff_file"
  fi
  if [[ -f "$_handoff_abs" ]]; then
    _hf_content="$(cat "$_handoff_abs" 2>/dev/null || true)"
  else
    _hf_content=""
  fi
  if [[ "$_hf_content" == *"work_handoff_v1"* ]]; then
    handoff_protocol="work_handoff_v1"
  elif [[ "$_hf_content" == *"expert_request_v1"* ]]; then
    handoff_protocol="expert_request_v1"
  elif [[ "$_hf_content" == *"expert_response_v1"* ]]; then
    handoff_protocol="expert_response_v1"
  fi
fi

if [[ "$handoff_expected" != "auto" && "$handoff_expected" != "yes" && "$handoff_expected" != "no" ]]; then
  handoff_expected="auto"
fi

handoff_required="no"
if [[ "$handoff_expected" == "yes" ]]; then
  handoff_required="yes"
elif [[ "$handoff_expected" == "auto" ]]; then
  if [[ -n "$handoff_file" || "$handoff_protocol" != "none" ]]; then
    handoff_required="yes"
  fi
fi

if [[ -n "$handoff_file" ]]; then
  handoff_evidence="handoff_file"
elif [[ "$handoff_required" == "no" ]]; then
  handoff_evidence="not_required"
elif [[ -n "$assumptions" || -n "$open_questions" || "$handoff_protocol" != "none" ]]; then
  handoff_evidence="inline_fields_or_protocol"
fi

handoff_status="not_applicable"
if [[ "$handoff_required" == "yes" && "$handoff_evidence" == "none" ]]; then
  handoff_status="missing_required_handoff"
elif [[ "$handoff_required" == "yes" ]]; then
  handoff_status="present"
fi

summary_text="${notes}"
if [[ "$summary_text" == *"summary="* ]]; then
  summary_text="${summary_text#*summary=}"
fi
summary_text="$(html_unescape "$summary_text")"

handoff_explanation="No handoff required for this run."
if [[ "$handoff_status" == "missing_required_handoff" ]]; then
  handoff_explanation="A handoff was expected, but no structured handoff evidence was captured."
elif [[ "$handoff_status" == "present" ]]; then
  handoff_explanation="Structured handoff evidence was captured."
fi

next_step="No action required."
if [[ "$handoff_status" == "missing_required_handoff" ]]; then
  next_step="Provide a structured handoff using work_handoff_v1 or expert_request_v1/expert_response_v1."
elif [[ "$status" != "ok" ]]; then
  next_step="Check command output and rerun the prompt after resolving errors."
fi
if [[ -n "$next_step_override" ]]; then
  next_step="$next_step_override"
fi

event_label="$action"
event_purpose="Audit hook lifecycle event."
detail_level="summary"
if [[ "$action" == "pre-message" ]]; then
  event_label="request_received"
  event_purpose="Prompt wrapper started and captured request context before command execution."
  detail_level="summary"
elif [[ "$action" == "post-message" ]]; then
  event_label="response_completed"
  event_purpose="Prompt wrapper finished command execution and persisted detailed trace output."
  detail_level="detailed"
fi

if [[ "$mode" == "full" ]]; then
  detail_level="detailed"
fi

render_event_block="yes"
if [[ "$mode" == "short" && "$action" == "pre-message" ]]; then
  render_event_block="no"
fi

if [[ -n "$communication_flow" ]]; then
  flow_svg_relpath="${audit_code}/sequence-flow.svg"
  timing_total_seconds=""
  [[ -n "$timing_total_ms" ]] && timing_total_seconds="$(format_duration_seconds "$timing_total_ms")"
  render_sequence_svg "$communication_flow" "${audit_asset_dir}/sequence-flow.svg" "$summary_text" "$timing_total_seconds"
fi

{
  if [[ "$append_rerun_marker" == "yes" && "$action" == "pre-message" ]]; then
    printf '## Rerun Start\n\n'
    printf -- '- timestamp: %s\n' "$timestamp_utc"
    printf -- '- message_id: %s\n' "${message_id:-not_provided}"
    printf -- '- summary: %s\n' "${summary_text:-n/a}"
    printf '\n'
  fi

  if [[ "$render_event_block" == "yes" ]]; then
    if [[ "$mode" == "full" && "$action" == "post-message" ]]; then
      printf '## Session Result\n\n'
      printf -- '- generated_at: %s\n' "$timestamp_utc"
      printf -- '- role: %s\n' "$role"
      printf '\n'
    else
      printf '## Event: %s (%s)\n\n' "$event_label" "$action"
      printf -- '- timestamp: %s\n' "$timestamp_utc"
      printf -- '- detail_level: %s\n' "$detail_level"
      printf -- '- status: %s\n' "$status"
      printf -- '- event_purpose: %s\n' "$event_purpose"
      if [[ -n "$notes" ]]; then
        printf -- '- notes: %s\n' "$notes"
      fi
      printf '\n'
    fi
  fi

  if [[ "$mode" == "full" ]]; then
    artifact_total="$(csv_count "$artifacts")"
    printf '### Summary\n\n'
    printf -- '- Executed command: %s\n' "${summary_text:-n/a}"
    printf -- '- Outcome: %s\n' "$status"
    if [[ -n "$timing_total_ms" ]]; then
      printf -- '- Runtime: %s\n' "$(format_duration_ms "$timing_total_ms")"
    fi
    printf -- '- Handoff check: %s\n' "$handoff_explanation"
    if [[ -n "$status_summary" ]]; then
      printf -- '- Status signal: %s\n' "$status_summary"
    fi
    if [[ "$artifact_total" != "0" ]]; then
      printf -- '- Artifact signal: %s curated artifact(s) captured for this run.\n' "$artifact_total"
    fi
    printf -- '- Recommended next step: %s\n' "$next_step"
    if [[ "$actor_count" -gt 1 ]]; then
      printf -- '- Collaboration signal: %s actors were observed in trace metadata.\n' "$actor_count"
    fi
    if [[ -n "$skills_trace" ]]; then
      printf -- '- Main capabilities involved: %s\n' "$skills_trace"
    fi
    if [[ -n "$mcp_endpoints_trace" ]]; then
      printf -- '- MCP endpoints involved: %s\n' "$mcp_endpoints_trace"
    fi
    printf '\n'

    if [[ -n "$flow_svg_relpath" ]]; then
      printf '### Flow Visualization\n\n'
      printf '![Communication flow](./%s)\n\n' "$flow_svg_relpath"
    fi

    printf '### Handoff Status\n\n'
    printf -- '- expectation: %s\n' "$handoff_expected"
    printf -- '- required: %s\n' "$handoff_required"
    printf -- '- status: %s\n' "$handoff_status"
    printf -- '- protocol: %s\n' "$handoff_protocol"
    printf -- '- evidence: %s\n' "$handoff_evidence"
    printf -- '- handoff_file: %s\n' "${handoff_file:-not_provided}"
    printf -- '- observed_actors: %s\n' "$actor_count"
    printf -- '- assumptions: %s\n' "${assumptions:-not_provided}"
    printf -- '- open_questions: %s\n' "${open_questions:-not_provided}"
    printf '\n'

    render_handoff_snippets_markdown "$artifacts" "$handoff_file"

    printf '<details>\n'
    printf '<summary>Technical details (for maintainers)</summary>\n\n'

    if [[ -n "$execution_stack" ]]; then
      printf '#### Execution Stack\n\n'
      printf '```text\n'
      printf '%s\n' "$execution_stack" | sed 's/ -> /\n-> /g'
      printf '```\n\n'
    fi

    if [[ -n "$skills_trace" || -n "$agents_trace" || -n "$instructions_trace" || -n "$mcp_endpoints_trace" ]]; then
      printf '#### Resolution Trace\n\n'
      if [[ -n "$skills_trace" ]]; then
        printf -- '- skills:\n'
        printf '%s\n' "$skills_trace" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed '/^$/d' | sed 's/^/  - /'
      fi
      if [[ -n "$agents_trace" ]]; then
        printf -- '- agents:\n'
        printf '%s\n' "$agents_trace" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed '/^$/d' | sed 's/^/  - /'
      fi
      if [[ -n "$instructions_trace" ]]; then
        printf -- '- instructions:\n'
        printf '%s\n' "$instructions_trace" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed '/^$/d' | sed 's/^/  - /'
      fi
      if [[ -n "$mcp_endpoints_trace" ]]; then
        printf -- '- mcp_endpoints:\n'
        printf '%s\n' "$mcp_endpoints_trace" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed '/^$/d' | sed 's/^/  - /'
      fi
      printf '\n'
    fi

    if [[ -n "$communication_flow" && -z "$flow_svg_relpath" ]]; then
      printf '#### Communication Trace (text fallback)\n\n'
      declare -a flow_rows=()
      IFS=';' read -r -a flow_rows <<<"$communication_flow"
      for row in "${flow_rows[@]:-}"; do
        trimmed="$(trim_text "$row")"
        [[ -n "$trimmed" ]] && printf -- '- %s\n' "$trimmed"
      done
      printf '\n'
    fi

    if [[ -n "$artifacts" ]]; then
      artifact_total="0"
      declare -a artifact_array=()
      IFS=',' read -r -a artifact_array <<<"$artifacts"
      artifact_total="${#artifact_array[@]}"
      printf '#### Artifact Overview\n\n'
      printf -- '- total: %s\n' "$artifact_total"

      group_count=0
      groups_output=""
      unset group_keys
      unset group_values
      declare -a group_keys
      declare -a group_values
      for artifact in "${artifact_array[@]:-}"; do
        trimmed="$(trim_text "$artifact")"
        [[ -n "$trimmed" ]] || continue
        group_key="$(artifact_group_key "$trimmed")"
        found_group="0"
        for ((group_index=0; group_index<group_count; group_index++)); do
          if [[ "${group_keys[$group_index]}" == "$group_key" ]]; then
            group_values[$group_index]="$(( ${group_values[$group_index]} + 1 ))"
            found_group="1"
            break
          fi
        done
        if [[ "$found_group" == "0" ]]; then
          group_keys[$group_count]="$group_key"
          group_values[$group_count]="1"
          group_count=$((group_count + 1))
        fi
      done
      if [[ "$group_count" -gt 0 ]]; then
        printf -- '- groups:\n'
        for ((group_index=0; group_index<group_count; group_index++)); do
          printf -- '  - %s: %s\n' "${group_keys[$group_index]}" "${group_values[$group_index]}"
        done
      fi
      printf '\n'

      printf '#### Key Artifacts\n\n'
      artifact_preview_limit=12
      artifact_rendered=0
      for artifact in "${artifact_array[@]:-}"; do
        trimmed="$(echo "$artifact" | xargs)"
        [[ -n "$trimmed" ]] || continue
        if [[ "$artifact_rendered" -ge "$artifact_preview_limit" ]]; then
          continue
        fi
        printf -- '- %s\n' "$trimmed"
        artifact_rendered=$((artifact_rendered + 1))
      done
      if [[ "$artifact_total" -gt "$artifact_preview_limit" ]]; then
        printf -- '- ... %s more omitted from the detailed list\n' "$((artifact_total - artifact_preview_limit))"
      fi
      printf '\n'

    fi

    if [[ -n "$timing_total_ms" || -n "$timing_pre_hook_ms" || -n "$timing_command_ms" ]]; then
      printf '#### Timing Breakdown\n\n'
      [[ -n "$timing_total_ms" ]] && printf -- '- total: %s\n' "$(format_duration_ms "$timing_total_ms")"
      [[ -n "$timing_pre_hook_ms" ]] && printf -- '- setup overhead: %s\n' "$(format_duration_ms "$timing_pre_hook_ms")"
      [[ -n "$timing_command_ms" ]] && printf -- '- task execution: %s\n' "$(format_duration_ms "$timing_command_ms")"
      printf '\n'
    fi

    printf '</details>\n\n'
  fi
} >>"$audit_file"

cat <<EOF
api_version: "v1"
kind: "task_audit_log"
status: "ok"
mode: "${mode}"
task_id: "${task_id}"
role: "${role}"
action: "${action}"
audit_file: "${audit_file}"
EOF
