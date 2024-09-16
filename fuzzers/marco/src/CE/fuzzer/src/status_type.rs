#[derive(Debug, Clone, Copy, PartialEq)]
pub enum StatusType {
    Normal,
    Timeout,
    Crash,
    Skip,
    Error,
}
