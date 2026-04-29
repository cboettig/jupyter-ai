export interface HarnessInfo {
  id: string;
  display_name: string;
  icon: string;
}

export interface ModelInfo {
  id: string;
  name: string;
}

export interface SessionMode {
  id: string;
  name: string;
}

export interface ConfigOption {
  id: string;
  name: string;
  value: unknown;
}

export interface AvailableCommand {
  name: string;
  description: string;
}

export interface ChatBridgeState {
  harness_id: string | null;
  selected_model_id?: string;
  available_models?: ModelInfo[];
  selected_mode_id?: string;
  session_modes?: SessionMode[];
  config_options?: ConfigOption[];
  available_commands?: AvailableCommand[];
}
