/**
 * Project GOZEN - 御前会議 型定義
 */

export type SessionPhase =
  | 'idle'
  | 'proposal'
  | 'objection'
  | 'merged'
  | 'merge_decision'
  | 'validation'
  | 'decision'
  | 'execution'
  | 'completed'
  | 'error';

export type CouncilMode = 'council' | 'execute';

export type MessageFrom = 'kaigun' | 'rikugun' | 'shoki' | 'genshu' | 'system';

export interface Proposal {
  title: string;
  summary: string;
  key_points: string[];
}

export interface ChatMessage {
  id: string;
  from: MessageFrom;
  type: 'proposal' | 'objection' | 'merged' | 'validation' | 'decision' | 'info' | 'error';
  content: Proposal | string;
  fullText?: string;
  timestamp: Date;
}

export interface DecisionOption {
  value: number;
  label: string;
}

// WebSocket メッセージ型

export interface WSPhaseMessage {
  type: 'PHASE';
  phase: SessionPhase;
  status: 'in_progress' | 'completed';
}

export interface WSProposalMessage {
  type: 'PROPOSAL';
  content: Proposal;
  fullText: string;
}

export interface WSObjectionMessage {
  type: 'OBJECTION';
  content: Proposal;
  fullText: string;
}

export interface WSMergedMessage {
  type: 'MERGED';
  content: Proposal;
  fullText: string;
}

export interface WSValidationMessage {
  type: 'VALIDATION';
  content: Proposal;
  fullText: string;
}

export interface WSAwaitingDecisionMessage {
  type: 'AWAITING_DECISION';
  options: DecisionOption[];
  loopCount?: number;
}

export interface WSAwaitingMergeDecisionMessage {
  type: 'AWAITING_MERGE_DECISION';
  options: DecisionOption[];
}

export interface WSApprovedStampMessage {
  type: 'APPROVED_STAMP';
}

export interface WSInfoMessage {
  type: 'INFO';
  from: string;
  content: string;
}

export interface WSCompleteMessage {
  type: 'COMPLETE';
  result: {
    approved: boolean;
    adopted: string | null;
    mode: CouncilMode;
    loop_count?: number;
  };
}

export interface WSErrorMessage {
  type: 'ERROR';
  message: string;
}

export type WSServerMessage =
  | WSPhaseMessage
  | WSProposalMessage
  | WSObjectionMessage
  | WSMergedMessage
  | WSValidationMessage
  | WSAwaitingDecisionMessage
  | WSAwaitingMergeDecisionMessage
  | WSApprovedStampMessage
  | WSInfoMessage
  | WSCompleteMessage
  | WSErrorMessage;

// クライアント → サーバー

export interface WSStartMessage {
  type: 'START';
  mission: string;
  mode: CouncilMode;
}

export interface WSDecisionMessage {
  type: 'DECISION';
  choice: number;
}

export interface WSMergeDecisionMessage {
  type: 'MERGE_DECISION';
  choice: number;
}

export type WSClientMessage = WSStartMessage | WSDecisionMessage | WSMergeDecisionMessage;
