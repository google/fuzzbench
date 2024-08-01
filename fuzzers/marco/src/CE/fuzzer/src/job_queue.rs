//use priority_queue::PriorityQueue;
use std::{self, cmp::Ordering};
//use std::path::{Path, PathBuf};

#[derive(Eq, PartialEq, Clone, Debug, Hash)]
pub struct SeedFilePath {
    // pub file_path: PathBuf,
    pub file_id: usize,
}

#[derive(Clone, Copy, Debug)]
pub struct PriorityValue {
    pub level: u16,
    pub rare_score: f32,
}
impl Ord for PriorityValue {
    fn cmp(&self, other: &PriorityValue) -> Ordering {
        match self.level.cmp(&other.level) {
            // this is fifo 
            // Ordering::Greater => Ordering::Less,//Ordering::Greater,
            // Ordering::Less => Ordering::Greater,//Ordering::Less,
            // this is rare 
            Ordering::Greater => Ordering::Greater,
            Ordering::Less => Ordering::Less,
            Ordering::Equal => {    
                if (self.rare_score - other.rare_score) > 0.01 {
                    Ordering::Greater
                }
                else if (other.rare_score - self.rare_score) > 0.01 {
                    Ordering::Less
                }
                else {
                    Ordering::Equal
                }
            },
        }
    }
}
impl PartialOrd for PriorityValue {
    fn partial_cmp(&self, other: &PriorityValue) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for PriorityValue {
    fn eq(&self, other: &Self) -> bool {
        (self.level == other.level) && (self.rare_score - other.rare_score).abs() < 0.01
    }
}

impl Eq for PriorityValue {}
