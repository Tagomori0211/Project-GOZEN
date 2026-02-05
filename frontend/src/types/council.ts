/**
 * Project GOZEN - 御前会議 型定義
 */

export type SessionPhase =
  | 'idle'
  | 'proposal'
  | 'objection'
  | 'merged'
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
  type: 'proposal' | 'objection' | 'merged' | 'decision' | 'info' | 'error';
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

export interface WSAwaitingDecisionMessage {
  type: 'AWAITING_DECISION';
  options: DecisionOption[];
}

export interface WSCompleteMessage {
  type: 'COMPLETE';
  result: {
    approved: boolean;
    adopted: string | null;
    mode: CouncilMode;
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
  | WSAwaitingDecisionMessage
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

export type WSClientMessage = WSStartMessage | WSDecisionMessage;
