type EmptyWrite = { [_ in never]: never };

export type EdgeDatabase = {
  public: {
    Tables: {
      projects: {
        Row: {
          id: number;
          project_id: string;
        };
        Insert: EmptyWrite;
        Update: EmptyWrite;
        Relationships: [];
      };
      operational_monitoring_snapshots: {
        Row: {
          id: number;
          project_pk: number;
          observed_at: string;
          heartbeat_state: string;
          heartbeat_observed_at: string | null;
          worker_state: string | null;
          heartbeat_reason: string;
          api_budget_state: string;
          api_budget_limit: number | null;
          api_budget_used: number | null;
          api_budget_remaining: number | null;
          api_budget_resets_at: string | null;
          api_budget_reason: string;
          stage_health_state: string;
          current_stage: string | null;
          stage_state: string | null;
          healthy_stage_count: number | null;
          failed_stage_count: number | null;
          stage_health_reason: string;
          queue_state: string;
          queue_depth: number | null;
          queue_capacity: number | null;
          queue_reason: string;
          failure_state: string;
          failure_count: number | null;
          failure_reason: string;
          artifact_state: string;
          artifact_fingerprint: string | null;
          artifact_committed_at: string | null;
          artifact_reason: string;
          map_state: string;
          map_fingerprint: string | null;
          map_refreshed_at: string | null;
          map_reason: string;
          model_state: string;
          yoloe_state: string;
          bioclip_state: string;
          model_reason: string;
          resource_state: string;
          free_disk_bytes: number | null;
          process_rss_bytes: number | null;
          memory_capacity_bytes: number | null;
          mps_allocated_bytes: number | null;
          mps_reserved_bytes: number | null;
          resource_reason: string;
          scientific_claim_allowed: false;
        };
        Insert: EmptyWrite;
        Update: EmptyWrite;
        Relationships: [];
      };
      media_objects: {
        Row: {
          id: number;
          project_pk: number;
          media_object_id: string;
          storage_backend: string;
          storage_key: string | null;
          media_state: string;
          content_sha256: string | null;
          byte_count: number | null;
          media_type: string | null;
          decode_status: string;
          rights_status: string;
          display_allowed: boolean;
          removed_at: string | null;
        };
        Insert: EmptyWrite;
        Update: EmptyWrite;
        Relationships: [];
      };
      runs: {
        Row: {
          id: number;
          project_pk: number;
          run_id: string;
        };
        Insert: EmptyWrite;
        Update: EmptyWrite;
        Relationships: [];
      };
      b2_signing_receipts: {
        Row: {
          signing_receipt_id: string;
          project_pk: number;
          media_object_pk: number;
          auth_user_id: string;
          method: string;
          ttl_seconds: number;
          issued_at: string;
          expires_at: string;
          request_fingerprint: string;
        };
        Insert: {
          signing_receipt_id: string;
          project_pk: number;
          media_object_pk: number;
          auth_user_id: string;
          method: string;
          ttl_seconds: number;
          issued_at: string;
          expires_at: string;
          request_fingerprint: string;
        };
        Update: EmptyWrite;
        Relationships: [];
      };
      server_action_receipts: {
        Row: {
          server_action_id: string;
          project_pk: number;
          run_pk: number;
          requested_by: string;
          action: "pause_run" | "resume_run" | "cancel_run";
          expected_revision: number;
          prior_status: string;
          result_status: string;
          result_revision: number;
          request_fingerprint: string;
          applied_at: string;
        };
        Insert: {
          server_action_id: string;
          project_pk: number;
          run_pk: number;
          requested_by: string;
          action: "pause_run" | "resume_run" | "cancel_run";
          expected_revision: number;
          request_fingerprint: string;
        };
        Update: EmptyWrite;
        Relationships: [];
      };
    };
    Views: { [_ in never]: never };
    Functions: { [_ in never]: never };
    Enums: { [_ in never]: never };
    CompositeTypes: { [_ in never]: never };
  };
};
