//use priority_queue::PriorityQueue;
use std::{self, cmp::Ordering};
use std::path::{Path, PathBuf};

#[derive(Clone, Debug)]
pub struct BcountPriorityValue {
    // by the order of ranking basis 
    // queueid > rare_score > seed_id
    pub queue_id: u32,  // 0: afl 1: grader 2: grader-ctrl 3: grader-path
    pub rare_score: u32, // big over small, real rareness * 10000 to avoid floating point calculation 
    pub seed_id: u32,    // small over big, LIFO 
    pub path: PathBuf    
}

impl Ord for BcountPriorityValue {
    fn cmp(&self, other: &BcountPriorityValue) -> Ordering {
        //the smaller the round, the higher the priority
        match self.queue_id.cmp(&other.queue_id) {            
            Ordering::Greater => Ordering::Less,
            Ordering::Less => Ordering::Greater,            
            Ordering::Equal => {    
                // the larger the rare score the better
                match self.rare_score.cmp(&other.rare_score) {
                    Ordering::Greater => Ordering::Greater,
                    Ordering::Less => Ordering::Less,
                    Ordering::Equal => { 
                        match self.seed_id.cmp(&other.seed_id) {
                            Ordering::Greater => Ordering::Greater,
                            Ordering::Less => Ordering::Less,
                            Ordering::Equal => Ordering::Equal
                        }
                    }
                }
            }
        }
    }
}

impl PartialOrd for BcountPriorityValue {
    fn partial_cmp(&self, other: &BcountPriorityValue) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for BcountPriorityValue {
    fn eq(&self, other: &Self) -> bool {
        // not going to happen though 
        (self.queue_id == other.queue_id) && (self.rare_score == other.rare_score) && (self.seed_id == other.seed_id)
    }
}

impl Eq for BcountPriorityValue {}




// #[derive(Clone, Copy, Debug)]
// pub struct BcountPriorityValue {
//     pub round: i32,  //1,2,3,
//     pub rare_score: u32,
// }
// impl Ord for BcountPriorityValue {
//     fn cmp(&self, other: &BcountPriorityValue) -> Ordering {
//         match self.round.cmp(&other.round) {
//             //the smaller the round, the higher the priority
//             Ordering::Greater => Ordering::Less,
//             Ordering::Less => Ordering::Greater,
//             // the larger the rare score the better
//             Ordering::Equal => {    
//                 self.rare_score.cmp(&other.rare_score)
//             },
//         }
//     }
// }
// impl PartialOrd for BcountPriorityValue {
//     fn partial_cmp(&self, other: &BcountPriorityValue) -> Option<Ordering> {
//         Some(self.cmp(other))
//     }
// }

// impl PartialEq for BcountPriorityValue {
//     fn eq(&self, other: &Self) -> bool {
//         (self.round == other.round) && (self.rare_score == other.rare_score)
//     }
// }

// impl Eq for BcountPriorityValue {}
