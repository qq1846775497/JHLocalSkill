# Key Files

## Plugin Root
`Plugins/PLBehaviorTreeSM/`

## Runtime Module (`PLBehaviorTreeSM`)
- `Source/PLBehaviorTreeSM/Private/BLBTStateMachineBlueprint.cpp` — Blueprint asset logic; creates `__HiddenK2CompatGraph__` for K2 compatibility.
- `Source/PLBehaviorTreeSM/Public/BLBTStateMachineBlueprint.h` — Asset header with `EnsureHiddenK2CompatGraph()`.
- `Source/PLBehaviorTreeSM/Private/BLBehaviorTreeStateMachine.cpp` — Runtime state machine logic.

## Editor Module (`PLBehaviorTreeSMEditor`)
- `Source/PLBehaviorTreeSMEditor/Private/BLBTStateMachineBlueprintEditor.cpp` — **Main custom editor**. Contains `FBLBTStateMachineBlueprintEditor`, `FBLBTStatesSummoner`, `FBLBTTransitionsSummoner`, `FBLBTDetailsSummoner`, `FBLBTStateMachineApplicationMode`, glass styling, and tab-close logic.
- `Source/PLBehaviorTreeSMEditor/Public/BLBTStateMachineBlueprintEditor.h` — Editor class declaration.
- `Source/PLBehaviorTreeSMEditor/Private/BLBTStateMachineCompiler.cpp` — Custom Kismet compiler; temporarily removes `StateMachineGraph` from `UbergraphPages` during `CreateFunctionList` to avoid `FKismetCompilerContext::IsNodePure` crash.
- `Source/PLBehaviorTreeSMEditor/Private/BLBTEditorStyle.h` — Cyan/glass color definitions and corner badge brush.
- `Source/PLBehaviorTreeSMEditor/Private/Graph/BLBTGraphNode_State.cpp/.h` — State node; has `BoundGraph` for Entry/Exit logic.
- `Source/PLBehaviorTreeSMEditor/Private/Graph/BLBTGraphNode_Transition.cpp/.h` — Transition node; renames bound graph to `EvaluateCondition_StateA_StateB`.
- `Source/PLBehaviorTreeSMEditor/Private/Graph/BLBTStateMachineGraphSchema.cpp/.h` — Schema for the main visual graph.
- `Source/PLBehaviorTreeSMEditor/Private/Graph/BLBTStateLogicGraphSchema.cpp/.h` — Schema for state Entry/Exit graphs (derives from `UEdGraphSchema_K2`).
- `Source/PLBehaviorTreeSMEditor/Private/Graph/BLBTTransitionGraphSchema.cpp/.h` — Schema for transition condition graphs (derives from `UEdGraphSchema_K2`).
