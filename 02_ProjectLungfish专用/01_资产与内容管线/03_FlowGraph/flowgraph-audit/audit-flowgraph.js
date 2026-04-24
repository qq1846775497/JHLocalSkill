#!/usr/bin/env node
// FlowGraph JSON Audit Script
// Usage: node audit-flowgraph.js <path-to-json> [--fix]
//
// Runs all checks from the flowgraph-audit SKILL.md checklist and prints a report.
// With --fix, writes a corrected copy to <original>_fixed.json

const fs = require('fs');
const path = require('path');

// ── Helpers ──────────────────────────────────────────────────────────────────

function isObserverNode(cls) {
  return /OnTrigger|OnActor|Listen|Observer/i.test(cls);
}

function isActionNode(cls) {
  return /ExecuteCustomEvent|SetGameplayTag|ModifyPhaseAttribute/i.test(cls);
}

function isSequenceNode(cls) {
  return /ExecutionSequence/i.test(cls);
}

function isMultiGateNode(cls) {
  return /MultiGate/i.test(cls);
}

function isSoundNode(cls) {
  return /PlaySound/i.test(cls);
}

function isWeatherNode(cls) {
  return /ChangeWeather/i.test(cls);
}

function isDialogueNode(cls) {
  return /Dialogue|DialogueHUD|DialogueBubble|AutoplayHudText/i.test(cls);
}

function isAIMoveNode(cls) {
  return /AIMoveToByTag/i.test(cls);
}

function isSpawnEntityNode(cls) {
  return /SpawnEntity/i.test(cls);
}

function isTeleportNode(cls) {
  return /Teleport/i.test(cls);
}

function isGuideTaskNode(cls) {
  return /GuideTask/i.test(cls);
}

function isDoNNode(cls) {
  return /FlowNode_DoN/i.test(cls);
}

function isSubGraphNode(cls) {
  return /SubGraph/i.test(cls);
}

function isBranchNode(cls) {
  return /FlowNode_Branch/i.test(cls);
}

function isTimerNode(cls) {
  return /Timer/i.test(cls);
}

function isCounterNode(cls) {
  return /PLCounter|Counter/i.test(cls);
}

function isDynamicPinNode(cls) {
  return /ActionChain/i.test(cls);
}

function isStartRootFlowNode(cls) {
  return /StartRootFlow/i.test(cls);
}

function isListenTagChangedNode(cls) {
  return /ListenTagChanged/i.test(cls);
}

// ── Checks ───────────────────────────────────────────────────────────────────

function checkDuplicateGuids(nodes) {
  const seen = new Map();
  const issues = [];
  for (const n of nodes) {
    if (seen.has(n.nodeGuid)) {
      issues.push({
        severity: 'CRITICAL',
        check: 'DuplicateGUID',
        message: `Duplicate GUID ${n.nodeGuid} on nodes "${n.nodeTitle || n.nodeClass}" and "${seen.get(n.nodeGuid)}"`,
        nodeGuid: n.nodeGuid,
      });
    }
    seen.set(n.nodeGuid, n.nodeTitle || n.nodeClass);
  }
  return issues;
}

function checkDanglingConnections(nodes) {
  const guidSet = new Set(nodes.map(n => n.nodeGuid));
  const issues = [];
  for (const n of nodes) {
    for (const [pin, conn] of Object.entries(n.connections || {})) {
      if (!guidSet.has(conn.targetNodeGuid)) {
        issues.push({
          severity: 'CRITICAL',
          check: 'DanglingConnection',
          message: `Node "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] pin "${pin}" targets nonexistent node ${conn.targetNodeGuid.slice(0,8)}`,
          nodeGuid: n.nodeGuid,
          pin,
        });
      }
    }
  }
  return issues;
}

function checkInvalidPinRefs(nodes) {
  const nodeMap = new Map(nodes.map(n => [n.nodeGuid, n]));
  const issues = [];
  for (const n of nodes) {
    for (const [pin, conn] of Object.entries(n.connections || {})) {
      const target = nodeMap.get(conn.targetNodeGuid);
      if (!target) continue; // caught by dangling check
      const hasPin = (target.inputPins || []).some(p => p.pinName === conn.targetPinName);
      if (!hasPin) {
        issues.push({
          severity: 'CRITICAL',
          check: 'InvalidPinRef',
          message: `Node "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] pin "${pin}" targets pin "${conn.targetPinName}" which doesn't exist on "${target.nodeTitle || target.nodeClass}" [${target.nodeGuid.slice(0,8)}]`,
          nodeGuid: n.nodeGuid,
          pin,
        });
      }
    }
  }
  return issues;
}

function checkOrphanedNodes(nodes) {
  const nodeMap = new Map(nodes.map(n => [n.nodeGuid, n]));
  // Build set of nodes that receive at least one incoming connection
  const hasIncoming = new Set();
  for (const n of nodes) {
    for (const conn of Object.values(n.connections || {})) {
      hasIncoming.add(conn.targetNodeGuid);
    }
  }
  // Also do reachability from Start
  const startNode = nodes.find(n => /FlowNode_Start/.test(n.nodeClass));
  const reachable = new Set();
  if (startNode) {
    const queue = [startNode.nodeGuid];
    while (queue.length) {
      const guid = queue.pop();
      if (reachable.has(guid)) continue;
      reachable.add(guid);
      const node = nodeMap.get(guid);
      if (!node) continue;
      for (const conn of Object.values(node.connections || {})) {
        queue.push(conn.targetNodeGuid);
      }
    }
  }

  const issues = [];
  for (const n of nodes) {
    if (/FlowNode_Start/.test(n.nodeClass)) continue;
    if (!hasIncoming.has(n.nodeGuid) && !reachable.has(n.nodeGuid)) {
      issues.push({
        severity: 'WARNING',
        check: 'OrphanedNode',
        message: `Node "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] has no incoming connections and is unreachable from Start`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkDeadEnds(nodes) {
  const issues = [];
  for (const n of nodes) {
    if ((n.outputPins || []).length > 0 && Object.keys(n.connections || {}).length === 0) {
      issues.push({
        severity: 'INFO',
        check: 'DeadEnd',
        message: `Node "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] has ${n.outputPins.length} output pin(s) but no outgoing connections`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkSuccessLimit(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (isObserverNode(n.nodeClass) && n.properties && n.properties.SuccessLimit === 0) {
      issues.push({
        severity: 'HIGH',
        check: 'SuccessLimitZero',
        message: `Observer "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] has SuccessLimit=0 — Success/Completed pin will never fire`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkEmptyIdentityTags(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!n.properties || !n.properties.IdentityTags) continue;
    if (n.properties.bUsePayloadActors) continue; // uses payload instead
    const tags = n.properties.IdentityTags.gameplayTags || [];
    if (tags.length === 0 && (isActionNode(n.nodeClass) || isObserverNode(n.nodeClass))) {
      issues.push({
        severity: 'HIGH',
        check: 'EmptyIdentityTags',
        message: `Node "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] has empty IdentityTags — matches nothing`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkNoneAssets(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!n.properties) continue;
    if (isWeatherNode(n.nodeClass)) {
      if (n.properties.PLWeather === 'None') {
        const wTag = n.properties.WeatherTag;
        if (!wTag || wTag.tagName === 'None') {
          issues.push({
            severity: 'HIGH',
            check: 'NoWeatherSource',
            message: `Weather node [${n.nodeGuid.slice(0,8)}] has PLWeather=None AND WeatherTag=None — no weather will apply`,
            nodeGuid: n.nodeGuid,
          });
        }
      }
    }
    if (isSoundNode(n.nodeClass)) {
      if (n.properties.AudioAsset === 'None' && n.properties.MetaSoundAsset === 'None') {
        issues.push({
          severity: 'HIGH',
          check: 'NoAudioSource',
          message: `Sound node [${n.nodeGuid.slice(0,8)}] has both AudioAsset=None and MetaSoundAsset=None — silent`,
          nodeGuid: n.nodeGuid,
        });
      }
    }
  }
  return issues;
}

function checkSequenceGaps(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isSequenceNode(n.nodeClass)) continue;
    const outPins = (n.outputPins || []).map(p => p.pinName);
    const connected = new Set(Object.keys(n.connections || {}));
    const missing = outPins.filter(p => !connected.has(p));
    if (missing.length > 0) {
      issues.push({
        severity: 'LOW',
        check: 'SequenceGap',
        message: `Sequence [${n.nodeGuid.slice(0,8)}] has unconnected output(s): ${missing.join(', ')} (of ${outPins.join(', ')})`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkMultiGateDegenerate(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isMultiGateNode(n.nodeClass)) continue;
    const totalOutputs = (n.outputPins || []).length;
    const connectedCount = Object.keys(n.connections || {}).length;
    if (connectedCount <= 1 && totalOutputs > 1) {
      const loop = n.properties && n.properties.bLoop;
      issues.push({
        severity: 'LOW',
        check: 'MultiGateDegenerate',
        message: `MultiGate [${n.nodeGuid.slice(0,8)}] has ${totalOutputs} outputs but only ${connectedCount} connected (bLoop=${!!loop})`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

// ── Checks #11-#15 (expanded) ────────────────────────────────────────────────

function checkEmptyDialogueText(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isDialogueNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    const text = n.properties.DialogueText;
    if (!text || text === '' || text === 'None') {
      issues.push({
        severity: 'HIGH',
        check: 'EmptyDialogueText',
        message: `Dialogue node "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] has empty/missing DialogueText`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkAIMoveNoTarget(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isAIMoveNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    const tag = n.properties.TargetActorTag;
    const useExact = n.properties.bUseExactLocation;
    if ((!tag || tag.tagName === 'None') && !useExact) {
      issues.push({
        severity: 'HIGH',
        check: 'AIMoveNoTarget',
        message: `AIMoveToByTag [${n.nodeGuid.slice(0,8)}] has TargetActorTag=None and bUseExactLocation=false — no movement target`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkSpawnEntityEmpty(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isSpawnEntityNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    if (n.properties.bGetSpawnParameterFromPython) continue;
    const infos = n.properties.EntitySpawnInfos;
    if (!infos || (Array.isArray(infos) && infos.length === 0)) {
      issues.push({
        severity: 'HIGH',
        check: 'SpawnEntityEmpty',
        message: `SpawnEntity [${n.nodeGuid.slice(0,8)}] has empty EntitySpawnInfos — nothing will spawn`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkTeleportNoDestination(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isTeleportNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    const tag = n.properties.TargetActorTag;
    const offset = n.properties.TeleportOffset;
    const hasTag = tag && tag.tagName && tag.tagName !== 'None';
    const hasOffset = offset && (offset.x !== 0 || offset.y !== 0 || offset.z !== 0);
    if (!hasTag && !hasOffset) {
      issues.push({
        severity: 'HIGH',
        check: 'TeleportNoDestination',
        message: `Teleport [${n.nodeGuid.slice(0,8)}] has TargetActorTag=None and TeleportOffset=(0,0,0) — no destination`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkGuideTaskIncomplete(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isGuideTaskNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    const regTag = n.properties.RegisterTaskTag;
    const groupTag = n.properties.GroupTagToComplete;
    if (!regTag || regTag.tagName === 'None') {
      issues.push({
        severity: 'HIGH',
        check: 'GuideTaskNoRegister',
        message: `GuideTask [${n.nodeGuid.slice(0,8)}] has no RegisterTaskTag — task cannot register`,
        nodeGuid: n.nodeGuid,
      });
    }
    if ((!regTag || regTag.tagName === 'None') && (!groupTag || groupTag.tagName === 'None')) {
      issues.push({
        severity: 'HIGH',
        check: 'GuideTaskIncomplete',
        message: `GuideTask [${n.nodeGuid.slice(0,8)}] has neither RegisterTaskTag nor GroupTagToComplete — fully unconfigured`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

// ── Checks #16-#25 (new) ────────────────────────────────────────────────────

function checkListenerNoStopWired(nodes) {
  const issues = [];
  // Build a set of (nodeGuid, pinName) that receive connections
  const incomingPins = new Set();
  for (const n of nodes) {
    for (const conn of Object.values(n.connections || {})) {
      incomingPins.add(`${conn.targetNodeGuid}::${conn.targetPinName}`);
    }
  }
  for (const n of nodes) {
    if (!isObserverNode(n.nodeClass)) continue;
    const hasStopPin = (n.inputPins || []).some(p => p.pinName === 'Stop');
    if (hasStopPin && !incomingPins.has(`${n.nodeGuid}::Stop`)) {
      issues.push({
        severity: 'WARNING',
        check: 'ListenerNoStopWired',
        message: `Observer "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] has Stop pin but nothing connects to it`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkDoNMaxCountZero(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isDoNNode(n.nodeClass)) continue;
    if (n.properties && n.properties.MaxCount === 0) {
      issues.push({
        severity: 'HIGH',
        check: 'DoNMaxCountZero',
        message: `DoN [${n.nodeGuid.slice(0,8)}] has MaxCount=0 — Execute pin will never fire`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkPayloadActorsNoSource(nodes) {
  const issues = [];
  const nodeMap = new Map(nodes.map(n => [n.nodeGuid, n]));
  const payloadProducers = new Set(['OnTriggerEnter', 'OnTriggerEvent', 'SpawnEntity', 'SpawnByGameplayTag', 'TriggerOverlapActors']);

  function hasPayloadSourceUpstream(nodeGuid, visited = new Set()) {
    if (visited.has(nodeGuid)) return false;
    visited.add(nodeGuid);
    const node = nodeMap.get(nodeGuid);
    if (!node) return false;
    for (const producer of payloadProducers) {
      if (node.nodeClass.includes(producer)) return true;
    }
    // Check upstream: find nodes that connect TO this node
    for (const n of nodes) {
      for (const conn of Object.values(n.connections || {})) {
        if (conn.targetNodeGuid === nodeGuid) {
          if (hasPayloadSourceUpstream(n.nodeGuid, visited)) return true;
        }
      }
    }
    return false;
  }

  for (const n of nodes) {
    if (!n.properties || !n.properties.bUsePayloadActors) continue;
    if (!hasPayloadSourceUpstream(n.nodeGuid)) {
      issues.push({
        severity: 'WARNING',
        check: 'PayloadActorsNoSource',
        message: `Node "${n.nodeTitle || n.nodeClass}" [${n.nodeGuid.slice(0,8)}] uses bUsePayloadActors but no upstream payload source found`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkSubGraphAssetNone(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isSubGraphNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    if (n.properties.Asset === 'None' || !n.properties.Asset) {
      issues.push({
        severity: 'HIGH',
        check: 'SubGraphAssetNone',
        message: `SubGraph [${n.nodeGuid.slice(0,8)}] has Asset=None — no child flow to execute`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkBranchNoAddOns(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isBranchNode(n.nodeClass)) continue;
    const addOns = n.addOns || [];
    if (addOns.length === 0) {
      issues.push({
        severity: 'HIGH',
        check: 'BranchNoAddOns',
        message: `Branch [${n.nodeGuid.slice(0,8)}] has no AddOn predicates — always takes default path`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkTimerZeroTimes(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isTimerNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    if (n.properties.CompletionTime === 0 && n.properties.StepTime === 0) {
      issues.push({
        severity: 'WARNING',
        check: 'TimerZeroTimes',
        message: `Timer [${n.nodeGuid.slice(0,8)}] has CompletionTime=0 and StepTime=0 — fires instantly`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkListenTagChangedEmpty(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isListenTagChangedNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    const added = (n.properties.ListenAddedTags && n.properties.ListenAddedTags.gameplayTags) || [];
    const removed = (n.properties.ListenRemovedTags && n.properties.ListenRemovedTags.gameplayTags) || [];
    if (added.length === 0 && removed.length === 0) {
      issues.push({
        severity: 'HIGH',
        check: 'ListenTagChangedEmpty',
        message: `ListenTagChanged [${n.nodeGuid.slice(0,8)}] has empty ListenAddedTags and ListenRemovedTags — listens for nothing`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkCounterGoalZero(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isCounterNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    if (n.properties.Goal !== undefined && n.properties.Goal <= 0) {
      issues.push({
        severity: 'HIGH',
        check: 'CounterGoalZero',
        message: `Counter [${n.nodeGuid.slice(0,8)}] has Goal=${n.properties.Goal} — already finished or unreachable`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkDynamicPinNoConfig(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isDynamicPinNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    const tags = (n.properties.ActionNodeTags && n.properties.ActionNodeTags.gameplayTags) || [];
    if (tags.length === 0) {
      issues.push({
        severity: 'WARNING',
        check: 'DynamicPinNoConfig',
        message: `ActionChain [${n.nodeGuid.slice(0,8)}] has empty ActionNodeTags — no dynamic output pins`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

function checkStartRootFlowNoAsset(nodes) {
  const issues = [];
  for (const n of nodes) {
    if (!isStartRootFlowNode(n.nodeClass)) continue;
    if (!n.properties) continue;
    if (n.properties.FlowAsset === 'None' || !n.properties.FlowAsset) {
      issues.push({
        severity: 'HIGH',
        check: 'StartRootFlowNoAsset',
        message: `StartRootFlow [${n.nodeGuid.slice(0,8)}] has no FlowAsset — no flow to start`,
        nodeGuid: n.nodeGuid,
      });
    }
  }
  return issues;
}

// ── Main ─────────────────────────────────────────────────────────────────────

function audit(jsonPath) {
  const raw = fs.readFileSync(jsonPath, 'utf8');
  const data = JSON.parse(raw);

  if (data.schema !== 'FlowGraphExporter/1.0') {
    console.error(`ERROR: Unsupported schema "${data.schema}". Expected "FlowGraphExporter/1.0".`);
    process.exit(1);
  }

  const nodes = data.nodes || [];
  const allIssues = [
    ...checkDuplicateGuids(nodes),
    ...checkDanglingConnections(nodes),
    ...checkInvalidPinRefs(nodes),
    ...checkOrphanedNodes(nodes),
    ...checkDeadEnds(nodes),
    ...checkSuccessLimit(nodes),
    ...checkEmptyIdentityTags(nodes),
    ...checkNoneAssets(nodes),
    ...checkSequenceGaps(nodes),
    ...checkMultiGateDegenerate(nodes),
    ...checkEmptyDialogueText(nodes),
    ...checkAIMoveNoTarget(nodes),
    ...checkSpawnEntityEmpty(nodes),
    ...checkTeleportNoDestination(nodes),
    ...checkGuideTaskIncomplete(nodes),
    ...checkListenerNoStopWired(nodes),
    ...checkDoNMaxCountZero(nodes),
    ...checkPayloadActorsNoSource(nodes),
    ...checkSubGraphAssetNone(nodes),
    ...checkBranchNoAddOns(nodes),
    ...checkTimerZeroTimes(nodes),
    ...checkListenTagChangedEmpty(nodes),
    ...checkCounterGoalZero(nodes),
    ...checkDynamicPinNoConfig(nodes),
    ...checkStartRootFlowNoAsset(nodes),
  ];

  // ── Report ───────────────────────────────────────────────────────────────

  const severityOrder = { CRITICAL: 0, HIGH: 1, WARNING: 2, LOW: 3, INFO: 4 };
  allIssues.sort((a, b) => (severityOrder[a.severity] ?? 5) - (severityOrder[b.severity] ?? 5));

  const startNodes = nodes.filter(n => /FlowNode_Start/.test(n.nodeClass)).length;
  const observerNodes = nodes.filter(n => isObserverNode(n.nodeClass));
  const slZero = observerNodes.filter(n => n.properties && n.properties.SuccessLimit === 0).length;

  console.log(`\n== FlowGraph Audit: ${data.assetName} ==\n`);
  console.log(`  Asset:     ${data.assetPath}`);
  console.log(`  Exported:  ${data.exportTimestamp}`);
  console.log(`  Nodes:     ${nodes.length} total, ${startNodes} Start, ${observerNodes.length} observers (SuccessLimit=0: ${slZero})`);
  console.log('');

  if (allIssues.length === 0) {
    console.log('  No issues found.\n');
    return { data, issues: allIssues };
  }

  const grouped = {};
  for (const issue of allIssues) {
    (grouped[issue.severity] = grouped[issue.severity] || []).push(issue);
  }

  for (const sev of ['CRITICAL', 'HIGH', 'WARNING', 'LOW', 'INFO']) {
    const items = grouped[sev];
    if (!items) continue;
    console.log(`  [${sev}] (${items.length})`);
    for (const i of items) {
      console.log(`    - [${i.check}] ${i.message}`);
    }
    console.log('');
  }

  console.log(`  Total: ${allIssues.length} issue(s)\n`);
  return { data, issues: allIssues };
}

// ── Entry Point ──────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const jsonPath = args.find(a => !a.startsWith('--'));

if (!jsonPath) {
  console.log('Usage: node audit-flowgraph.js <path-to-json>');
  console.log('');
  console.log('Example:');
  console.log('  node .claude/skills/flowgraph-audit/audit-flowgraph.js Main/FlowGraphExports/FA_TestCangmuyuan202407.json');
  process.exit(0);
}

const resolved = path.resolve(jsonPath);
if (!fs.existsSync(resolved)) {
  console.error(`File not found: ${resolved}`);
  process.exit(1);
}

audit(resolved);
