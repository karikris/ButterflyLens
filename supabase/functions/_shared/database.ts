type EmptyWrite = { [_ in never]: never };

export type EdgeDatabase = {
  public: {
    Tables: {
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
