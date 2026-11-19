//! seam-check: mechanically check the cross-repo seam contracts written in
//! issues. A port of the pulseengine-claude plugin's seam-check.py with the
//! same CLI, output text and exit codes (0 pass, 1 fail, 2 cannot check);
//! YAML is read with rivet's own parser, rivet-yaml.

pub mod check;
pub mod cli;
pub mod json;
pub mod pyval;
pub mod selftest;
pub mod text;
pub mod transport;
