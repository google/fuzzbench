---
layout: default
title: Publications
has_children: false
nav_order: 9
permalink: /publications/
---

# Publications

[FuzzBench](https://dl.acm.org/doi/pdf/10.1145/3468264.3473932)
[[BibTeX](https://google.github.io/fuzzbench/faq/#how-can-i-cite-fuzzbench-in-my-paper)]
has been widely used by many research works to evaluate fuzzers and will
continue to serve on facilitating fuzzing evaluation for both academia and
the industry.
You are more than welcome to reach out to us to evaluate your fuzzers.

FuzzBench has the honor in helping the following publications by providing either an
evaluation framework or benchmark programs.

<!---
[//]: # (Only included publications of top venues.)
[//]: # (Citations are in Chicago style.)
[//]: # (Include the following links of each publication, if available:)
[//]: # (1. Full Paper.)
[//]: # (2. Our FuzzBench report.)
[//]: # (3. Slides.)
[//]: # (4. Video.)
[//]: # (5. BibTeX.)
-->

## 2022
* Zhang, Zenong, Zach Patterson, Michael Hicks, and Shiyi Wei.
  ["{FIXREVERTER}: A Realistic Bug Injection Methodology for Benchmarking Fuzz
  Testing."](https://www.usenix.org/system/files/sec22-zhang-zenong.pdf) In 31st
  USENIX Security Symposium (USENIX Security 22), pp. 3699-3715. 2022.
  { [Video](https://youtu.be/8n0GVJGvF7w)
  | [BibTeX](https://www.usenix.org/biblio/export/bibtex/281412)
  }
* Asprone, Dario, Jonathan Metzman, Abhishek Arya, Giovani Guizzo, and Federica
  Sarro. ["Comparing Fuzzers on a Level Playing Field with FuzzBench."](https://discovery.ucl.ac.uk/id/eprint/10144606/1/Comparing%20Fuzzers%20on%20a%20Level%20Playing%20Field%20with%20FuzzBench.pdf)
  In 2022 IEEE Conference on Software Testing, Verification and Validation
  (ICST), pp. 302-311. IEEE, 2022.
* Chen, Ju, Wookhyun Han, Mingjun Yin, Haochen Zeng, Chengyu Song, Byoungyoung
  Lee, Heng Yin, and Insik Shin. ["{SYMSAN}: Time and Space Efficient Concolic
  Execution via Dynamic Data-flow Analysis."](https://www.usenix.org/system/files/sec22-chen-ju.pdf)
  In 31st USENIX Security Symposium (USENIX Security 22), pp. 2531-2548. 2022.
  { [Slides](https://www.usenix.org/system/files/sec22_slides-chen_ju.pdf)
  | [Video](https://youtu.be/kactPkTffIo)
  | [BibTeX](https://www.usenix.org/biblio/export/bibtex/281360)
  }
* Zhang, Zenong, George Klees, Eric Wang, Michael Hicks, and Shiyi Wei.
  ["Registered Report: Fuzzing Configurations of Program
  Options."](https://www.ndss-symposium.org/wp-content/uploads/fuzzing2022_23008_paper.pdf)
* Fioraldi, Andrea, Alessandro Mantovani, Dominik Maier, and Davide Balzarotti.
  ["Registered Report: Dissecting American Fuzzy Lop."](https://www.eurecom.fr/publication/6832/download/sec-publi-6832.pdf) (2022).
* Ahmed, Alif, Jason D. Hiser, Anh Nguyen-Tuong, Jack W. Davidson, and Kevin
  Skadron. ["BigMap: Future-proofing Fuzzers with Efficient Large Maps."](https://alifahmed.github.io/res/BigMap_DSN.pdf)
  In 2021 51st Annual IEEE/IFIP International Conference on Dependable Systems
  and Networks (DSN), pp. 531-542. IEEE, 2021.
* Chen, Ju, Jinghan Wang, Chengyu Song, and Heng Yin. ["JIGSAW: Efficient and
  Scalable Path Constraints Fuzzing."](https://www.cs.ucr.edu/~heng/pubs/jigsaw_sp22.pdf)
  In 2022 IEEE Symposium on Security and Privacy (SP), pp. 1531-1531. IEEE Computer Society, 2022.
* Böhme, Marcel, László Szekeres, and Jonathan Metzman.
  ["On the Reliability of Coverage-Based Fuzzer Benchmarking."](http://seclab.cs.sunysb.edu/lszekeres/Papers/ICSE22.pdf)
  In 44th IEEE/ACM International Conference on Software Engineering, ser. ICSE,
  vol. 22. 2022.
* Vishnyakov, Alexey, Daniil Kuts, Vlada Logunova, Darya Parygina, Eli Kobrin,
  Georgy Savidov, and Andrey Fedotov. ["Sydr-Fuzz: Continuous Hybrid Fuzzing and
  Dynamic Analysis for Security Development Lifecycle."](https://arxiv.org/pdf/2211.11595.pdf)
  In 2022 Ivannikov ISPRAS Open Conference (ISPRAS), pp. 111-123, IEEE, 2022.
  { [Evaluation](https://sydr-fuzz.github.io/fuzzbench/) }


## 2021
* Metzman, Jonathan, László Szekeres, Laurent Simon, Read Sprabery, and
  Abhishek Arya. ["FuzzBench: an open fuzzer benchmarking platform and
  service."](https://dl.acm.org/doi/pdf/10.1145/3468264.3473932)
  In Proceedings of the 29th ACM Joint Meeting on European Software Engineering
  Conference and Symposium on the Foundations of Software Engineering, pp.
  1393-1403. 2021.
* Wang, Jinghan, Chengyu Song, and Heng Yin. ["Reinforcement learning-based
  hierarchical seed scheduling for greybox
  fuzzing."](https://escholarship.org/uc/item/44p2v1gd) (2021).
* Zhu, Xiaogang, and Marcel Böhme. ["Regression greybox fuzzing."](https://mboehme.github.io/paper/CCS21.pdf)
  In Proceedings of the 2021 ACM SIGSAC Conference on Computer and
  Communications Security, pp. 2169-2182. 2021.
* Poeplau, Sebastian, and Aurélien Francillon. ["SymQEMU: Compilation-based
  symbolic execution for binaries."](http://193.55.114.4/docs/ndss21_symqemu.pdf)
  In NDSS. 2021.
* Gao, Xiang, Gregory J. Duck, and Abhik Roychoudhury. ["Scalable Fuzzing of
  Program Binaries with E9AFL."](https://www.comp.nus.edu.sg/~gregory/papers/e9afl.pdf)
  In 2021 36th IEEE/ACM International Conference on Automated Software
  Engineering (ASE), pp. 1247-1251. IEEE, 2021.


## 2020
* Fioraldi, Andrea, Dominik Maier, Heiko Eißfeldt, and Marc Heuse. ["{AFL++}:
  Combining Incremental Steps of Fuzzing
  Research."](https://escholarship.org/uc/item/44p2v1gd) In 14th USENIX Workshop on
  Offensive Technologies (WOOT 20). 2020.
  { [Slides](https://www.usenix.org/system/files/woot20-paper36-slides-fioraldi.pdf)
  | [Video](https://youtu.be/cZidm6I7KWU)
  | [BibTeX](https://www.usenix.org/biblio/export/bibtex/257204)
  }
