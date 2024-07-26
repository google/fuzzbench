#!/usr/bin/python3
from queue import PriorityQueue
from scipy.stats import beta
import networkit as nk
import numpy as np
import argparse
import logging
import time
import os
import random 

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('./Gscheduler.log')
formatter    = logging.Formatter('%(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# index of queue_count
FZQID = 0
CEQID = 1
# index of last_graph_topo
EDGECNT = 0
NODECNT = 1
UNVICNT = 2
# status of nodes
ALIVE=0
DEAD=1
EXPLD=2
# ceiling count of pc per node before EXPLD
MAXPC=5000

def parse_args():
    p = argparse.ArgumentParser("")
    p.add_argument("-d", dest="hybrid_mode", type=int, default=0, help="0: vanilla mode; 1: fz attempt modeled")
    p.add_argument("-m", dest="sched_mode", type=int, default=2, help="0: fifo(deprecated); 1: full-fledged for unvisited mode only; 2: full-fledged; 3: MC mode, p is ratio, r is 0/1; 4: random flip one from last path; 5: CFG-directed")
    return p.parse_args()

class Node():
    def __init__(self, key="", score=0.0):
        self.key = key
        self.pcqueue = PriorityQueue()
        self.status = ALIVE
        self.parentKey = "Root"
        if "-" in key:
            self.parentKey = key.split("-")[0]

        # CE perspective
        self.score = score
        self.attempt = 0
        self.win = 0
        self.visit = 0

        # FZ perspective
        self.fz_trace = set()
        self.fz_latest_cycle = 0    # TODO: fz_latest_cycle

class Gsched():
    def __init__(self, hybrid_mode, sched_mode):
        self.h_mode = hybrid_mode
        self.s_mode = sched_mode
        self.rnd = np.random.RandomState(7)

        if self.s_mode == 4:
            self.fifo_record = []
            self.fifo_record1 = []
            self.maxrecord = 150000
            

        ''' --------- graph initialization -------- '''
        self.G = nk.Graph(1, weighted=True, directed=True)
        self.addr_nodeid = {"Root": 0}
        self.node_attrs = [Node("Root", self.rnd.beta(1, 1))]

        ''' --------- global housekeeping info -------- '''
        self.queue_count = [0, 0]                        # fzq, ceq count
        self.ceq_decid = []                              # track all decision nodes, to update win count
        self.total_traces = 0

        ''' --------- current trace parsing; reset every new trace -------- '''
        self.cur_edgebeg = 0
        self.cur_tracesz = 0
        self.cur_traceid = -1
        self.cur_queueid = -1
        self.last_traceid = -1
        self.last_queueid = -1


        ''' --------- graph query cache -------- '''
        self.calcList = []
        self.new_calcNode = []                           # new node without score
        self.latest_nodes_rank = []
        self.latest_node_choice = -1
        self.node_check = False
        self.last_graph_topo = [0, 0, 0]                 # edgecnt, nodecnt, unviscnt

        ''' --------- decision profiling -------- '''
        self.sched_round_all = 0    # including all result, unsat/duppp/normal
        self.sched_round_brc = 0
        self.compute_round = 0
        self.leafpick = 0
        self.intepick = 0

        self.solve_unsat = 0
        self.solve_duppp = 0
        self.solve_normal = 0

        ''' --------- cost profiling -------- '''
        self.sched_cost = 0.0
        self.update_cost = 0.0


    def log_progress(self):

        logger.info("[checkpoint]: round %d, BRC: %d, compute: %d"%(
            self.sched_round_all, self.sched_round_brc, self.compute_round))

        logger.info("leafpick: %d, intepick: %d"%(
            self.leafpick, self.intepick))

        logger.info("outcomes: %d normal, %d unsat, %d dup-prefix"%(
            self.solve_normal, self.solve_unsat, self.solve_duppp))

        logger.info("graphtopo: %d nodes, %d edges, %d unvisited"%(
            self.last_graph_topo[NODECNT],
            self.last_graph_topo[EDGECNT],
            self.last_graph_topo[UNVICNT]))

        logger.info("sched cost: %fs, update_cost: %fs"%(
            self.sched_cost, self.update_cost))

    def reset_for_new_trace(self):
        if self.last_queueid != self.cur_queueid and self.last_traceid != self.cur_traceid:
            self.total_traces += 1
            self.last_queueid = self.cur_queueid
            self.last_traceid = self.cur_traceid

        self.cur_edgebeg = 0
        self.cur_tracesz = 0
        self.cur_traceid = -1
        self.cur_queueid = -1
        self.node_check = False

    def do_aftermath(self, record):
        if "UNSAT" in record:
            self.solve_unsat += 1
            self.node_attrs[self.latest_node_choice].status = DEAD
        if "DUP" in record:
            self.solve_duppp += 1
        if self.topo_changed():
            return True
        return False

    def topo_changed(self):
        cur_edgecnt = self.G.numberOfEdges()
        cur_nodecnt = self.G.numberOfNodes()
        cur_unvisited = len([i for i in self.G.iterNodes() if self.node_attrs[i].visit == 0])

        if cur_nodecnt > self.last_graph_topo[NODECNT] or cur_unvisited > self.last_graph_topo[UNVICNT] or cur_edgecnt > self.last_graph_topo[EDGECNT]:
            self.last_graph_topo = [cur_edgecnt, cur_nodecnt, cur_unvisited]
            return True
        else:
            return False

    def valid_old_queue(self):
        self.latest_nodes_rank = [(i, j) for (i, j) in self.latest_nodes_rank if not self.node_attrs[i].pcqueue.empty()]
        if self.latest_nodes_rank:
            return True
        return False

    def add_pcids(self, treedepth, nodeid, PC_ids, extra, isinteresting):
        if isinteresting:
            self.node_attrs[nodeid].pcqueue.put((0, "#".join([PC_ids, extra])))
        else:
            self.node_attrs[nodeid].pcqueue.put((treedepth, "#".join([PC_ids, extra])))

        if (self.node_attrs[nodeid].attempt + self.node_attrs[nodeid].pcqueue.qsize()) >= MAXPC:
            self.node_attrs[nodeid].status = EXPLD


    def add_one(self, record):
        brc_ids, PC_ids = record.strip("\n").split("@")
        addr, ctxh, tkdir, label, self.cur_traceid, self.cur_queueid = [int(i) for i in brc_ids.replace(" ", "").strip("\n").split("-")]

        # track dep building length
        cur_loc = self.cur_tracesz
        self.cur_tracesz += 1

        ''' ---------- for random flipper ---------- ''' 
        if self.s_mode == 4:
            if "none" not in PC_ids:
                PC_ids, extra = PC_ids.split("#")
                PC_ids += "-%d-%d-%d-%d"%(cur_loc, tkdir, self.cur_traceid, label)
                self.fifo_record.append("#".join([PC_ids, extra]))
            return 

        ''' ---------- build the graph ---------- '''
        addr = "0x%x_%d_0"%(addr, ctxh)

        # brc triplet
        p_root = "%s"%(addr)
        child_T ="%s-%d"%(addr, tkdir)
        child_F = "%s-%d"%(addr, 1-tkdir)

        # step 1. topo update related
        if p_root not in self.addr_nodeid:
            # update nodeid lookup dict
            for each in [p_root, child_T, child_F]:
                self.addr_nodeid[each] = len(self.addr_nodeid)
                if self.s_mode == 5:
                    self.node_attrs.append(Node(each, 0))
                else:
                    self.node_attrs.append(Node(each, self.rnd.beta(1, 1)))

            # update node in the graph
            self.G.addNodes(3)

            Pnodeid = self.addr_nodeid[p_root]
            Tnodeid = self.addr_nodeid[child_T]
            Fnodeid = self.addr_nodeid[child_F]

            self.new_calcNode += [Pnodeid, Tnodeid, Fnodeid]

            # update edge in the graph, concrete edge
            self.G.addEdge(self.cur_edgebeg, Pnodeid, w=1.0)
            self.G.addEdge(Pnodeid, Tnodeid, w=1.0)

            # update edge in the graph, symbolic edge
            self.G.addEdge(Pnodeid, Fnodeid, w=0.0)

        else:
            Pnodeid = self.addr_nodeid[p_root]
            Tnodeid = self.addr_nodeid[child_T]
            Fnodeid = self.addr_nodeid[child_F]

            # update edge in the graph, concrete edge
            self.G.increaseWeight(self.cur_edgebeg, Pnodeid, 1.0)
            self.G.increaseWeight(Pnodeid, Tnodeid, 1.0)

            # feedback update for ceq seeds
            if self.cur_queueid == 1 and self.cur_traceid >= 0:
                nodechoice = self.ceq_decid[self.cur_traceid]
                # update win count, once per trace (only when visited);
                if nodechoice == Tnodeid and self.node_check == False:
                    self.node_attrs[nodechoice].win += 1
                    self.node_check = True
                    # logger.info("win update node %d in trace (%d): win: %d, attempt: %d"%(
                    #     nodechoice, self.cur_traceid,
                    #     self.node_attrs[nodechoice].win, self.node_attrs[nodechoice].attempt))
        # step 2. irrelevant to topology
        # pcset
        if "none" not in PC_ids and self.node_attrs[Fnodeid].status != EXPLD:
            PC_ids, extra = PC_ids.split("#")
            treedepth = [int(i) for i in PC_ids.replace(" ", "").strip("\n").split("-")][-1]
            PC_ids += "-%d-%d-%d-%d"%(cur_loc, tkdir, self.cur_traceid, label)
            self.add_pcids(treedepth, Fnodeid, PC_ids, extra, (True if PC_ids.startswith("1") else False))

        # handle fuzzing trace differently for different hybrid mode
        if self.h_mode == 1: # model the fuzzer attempt!
            if self.cur_queueid == CEQID:
                self.node_attrs[Pnodeid].visit += 1
                self.node_attrs[Tnodeid].visit += 1
            else:
                self.node_attrs[Pnodeid].fz_trace.add(self.cur_traceid)
                self.node_attrs[Tnodeid].fz_trace.add(self.cur_traceid)
                # TODO: latest fz cycle?
        else:               # fzq are just extra corpus
            self.node_attrs[Pnodeid].visit += 1
            self.node_attrs[Tnodeid].visit += 1

        # reset edge begin node for next node
        self.cur_edgebeg = Tnodeid

    def pick_one(self, edge_p_dict):
        res = {}
        for i in self.G.iterNodes():
            # only compute score for actionable nodes
            if i != 0 and "-" in self.node_attrs[i].key and not self.node_attrs[i].pcqueue.empty():
                # mode 1: skip score collection for interior node
                if self.s_mode == 1 and self.node_attrs[i].visit != 0:
                    continue
                # score before discount
                sumscore = self.node_attrs[i].score
                parentNodeId = self.addr_nodeid[self.node_attrs[i].parentKey]
                p = edge_p_dict[(parentNodeId, i)]
                res[i] = sumscore * p
        # sort by the discounted score
        actable_ones = {k:v for k,v in sorted(res.items(), key=lambda item: item[1], reverse=True)}

        # set the frequency to flush and recompute graph
        flushfreq = int(self.G.numberOfNodes() / 3)
        return list(actable_ones.items())[:flushfreq]

    
    # prioritize branches by cfg-directed approach 
    def cfg_one(self, fifo):
        # step 1. init reward; 0 for unvisited, 999999 for visited (not going to be revisited)
        self.init_reward()

        # step 2. circle-free list 
        tmplist = self.POT_iterative()

        # step 3. node score recomputation 
        for i in range(0, len(tmplist)):
            curNodeId = tmplist[i]
            # skip root or leaf node
            if self.G.degreeOut(curNodeId) == 0 or curNodeId == 0:
                continue
            # get list of child nodes 
            child_score_list = [self.node_attrs[child].score for child in self.G.iterNeighbors(curNodeId)]
            self.node_attrs[curNodeId].score = min(child_score_list) + 0.5
            # logger.info("node %d, %s, score %f"%(curNodeId, self.node_attrs[curNodeId].key, self.node_attrs[curNodeId].score))
            # logger.info("Child list: %s"%(str([self.node_attrs[child].key for child in self.G.iterNeighbors(curNodeId)])))
        
        # step 4. rank actionable nodes by score+attempt 
        res = {}
        for i in self.G.iterNodes():
            # only compute score for actionable nodes
            if i != 0 and "-" in self.node_attrs[i].key and not self.node_attrs[i].pcqueue.empty():
                # take node score and attempt number as the ranking metric, go for lowest one 
                res[i] = self.node_attrs[i].score + self.node_attrs[i].attempt
        actable_ones = {k:v for k,v in sorted(res.items(), key=lambda item: item[1], reverse=False)}
        finalist = list(actable_ones.items()) 
        
        # 4. chosen node, inc attempt by 1 
        self.latest_node_choice, topNodeScore = finalist.pop(0)
        logger.info("cfg choice: nodeid %d, score %f"%(self.latest_node_choice, topNodeScore))
        PC_ids = self.node_attrs[self.latest_node_choice].pcqueue.get()[1]
        PC_ids, extra = PC_ids.split("#")
        is_good, qid, self.pp_hash, treedepth, plen, conc_dir, tid, nid = [int(i) for i in PC_ids.replace(" ", "").strip("\n").split("-")]
        
        extra = extra.replace(".", "#")
        extra = extra.replace(",", ".")

        res = "%d,%d,%d,%d,%d,%d,%s,\n"%(qid, tid, nid, conc_dir, plen, self.pp_hash, extra)
        fifo.write(res)
        fifo.flush()


    def random_one(self, fifo):
        if len(self.fifo_record):
            logger.info("max=%d"%(len(self.fifo_record)))
            if len(self.fifo_record) == 1:
                rdm_index = 0
            else:
                rdm_index = random.randint(0, len(self.fifo_record)-1)
            logger.info("randompick=%d"%(rdm_index))
            PC_ids = self.fifo_record[rdm_index]
            del self.fifo_record[rdm_index]
        else:
            logger.info("1max=%d"%(len(self.fifo_record1)))
            if len(self.fifo_record1) == 1:
                rdm_index = 0
            else:
                rdm_index = random.randint(0, len(self.fifo_record1)-1)
                
            logger.info("1random=%d"%(rdm_index))
            PC_ids = self.fifo_record1[rdm_index]
            del self.fifo_record1[rdm_index]

        PC_ids, extra = PC_ids.split("#")
        is_good, qid, self.pp_hash, treedepth, plen, conc_dir, tid, nid = [int(i) for i in PC_ids.replace(" ", "").strip("\n").split("-")]
        extra = extra.replace(".", "#")
        extra = extra.replace(",", ".")
        res = "%d,%d,%d,%d,%d,%d,%s,\n"%(qid, tid, nid, conc_dir, plen, self.pp_hash, extra)
        
        fifo.write(res)
        fifo.flush()        

    def sched_one(self, fifo, rerank=True):
        self.sched_round_all += 1

        if rerank or not self.valid_old_queue():
            edge_p_dict = self.graphUpdate()
            self.latest_nodes_rank = self.pick_one(edge_p_dict)

        if not self.latest_nodes_rank:      # FIXME: bug for early termination?
            logger.info("No valid node for scheduling!")
            exit(1)

        self.latest_node_choice, topNodeScore = self.latest_nodes_rank.pop(0)
        PC_ids = self.node_attrs[self.latest_node_choice].pcqueue.get()[1]
        PC_ids, extra = PC_ids.split("#")
        is_good, qid, self.pp_hash, treedepth, plen, conc_dir, tid, nid = [int(i) for i in PC_ids.replace(" ", "").strip("\n").split("-")]
        if is_good:
            self.sched_round_brc += 1
        extra = extra.replace(".", "#")
        extra = extra.replace(",", ".")

        res = "%d,%d,%d,%d,%d,%d,%s,\n"%(qid, tid, nid, conc_dir, plen, self.pp_hash, extra)
        fifo.write(res)
        fifo.flush()

        # log decision from leaf or interior
        if self.node_attrs[self.latest_node_choice].visit == 0:
            self.leafpick += 1
        else:
            self.intepick += 1

    def POT_iterative(self):
        s1 = []
        s2 = []
        visited = [0]
        s1.append(0)
        while s1:
            node = s1.pop()
            s2.append(node)
            for i in self.G.iterNeighbors(node):
                if i not in visited:
                    s1.append(i)
                    visited.append(i)
        s2.reverse()
        return s2

    def init_reward(self):
        leaflist = [i for i in self.G.iterNodes() if i != 0 and self.G.degreeOut(i) == 0 and self.node_attrs[i].status != DEAD]

        # for i in leaflist:
        #     self.node_attrs[i].score = 1.0
            # if self.node_attrs[i].visit == 0:
            #     self.node_attrs[i].score = 1.0
            # else:
            #     self.node_attrs[i].score = 0.0
        if self.s_mode == 3:        # 0/1 version
            for i in leaflist:
                if self.node_attrs[i].visit == 0:
                    self.node_attrs[i].score = 1.0
                else:
                    self.node_attrs[i].score = 0.0
        elif self.s_mode in [1,2]:  # TS based reward generation
            for i in leaflist:
                B = self.node_attrs[i].attempt + self.node_attrs[i].visit
                self.node_attrs[i].score = self.rnd.beta(1, 1+B)
        elif self.s_mode == 5:      # cfg directed mode 
            leaflist = [i for i in self.G.iterNodes() if i != 0 and self.G.degreeOut(i) == 0]
            for i in leaflist:
                if self.node_attrs[i].visit == 0:
                    self.node_attrs[i].score = 999999
                else:
                    self.node_attrs[i].score = 0


    def graphUpdate(self):
        self.compute_round += 1

        # step 1. init reward
        self.init_reward()

        # step 2. circle-free graph traversal
        if len(self.new_calcNode) > 0.1 * len(self.calcList):
            self.calcList = self.POT_iterative()
            self.new_calcNode = []
            tmplist = self.calcList
        else:
            tmplist = list(reversed(self.new_calcNode)) + self.calcList

        # step 3. node score recomputation
        edge_p_dict = {}
        for i in range(0, len(tmplist)):
            curNodeId = tmplist[i]
            # skip leaf & root
            if self.G.degreeOut(curNodeId) == 0 or curNodeId == 0:
                continue
            # interior node, compute s before discount
            edge_p_dict = self.updateScore(curNodeId, edge_p_dict)

        # output the transition probability of each edge, for discount factor
        return edge_p_dict

    def updateScore(self, curNodeId, edge_p_dict):
        isdeterP = 0 if "-" in self.node_attrs[curNodeId].key else 1
        all_p = []
        all_score = []

        for i in self.G.iterNeighbors(curNodeId):
            # compute on site if not exist
            if (curNodeId, i) not in edge_p_dict:
                edge_p_dict[(curNodeId, i)] = self.updateTranProb(curNodeId, i, isdeterP, edge_p_dict)
            all_p.append(edge_p_dict[(curNodeId, i)])
            all_score.append(self.node_attrs[i].score)

        # normalize all_p & aggregate all_score
        self.node_attrs[curNodeId].score = 0.0
        if sum(all_p) > 0:
            all_p = [float(i)/sum(all_p) for i in all_p]
            for i in range(0, len(all_p)):
                self.node_attrs[curNodeId].score += (all_p[i] * all_score[i])
        return edge_p_dict

    def updateTranProb(self, begnode, endnode, isdeterP, edge_p_dict):
        if self.node_attrs[endnode].status == DEAD:
            return 0.0

        if self.s_mode == 3: # MC mode, transition is ratio
            P_visit = self.node_attrs[begnode].visit + self.node_attrs[begnode].attempt
            A = self.G.weight(begnode, endnode)
            B = P_visit - A
            p =  self.rnd.beta(1+A, 1+B)
            return p

        if self.s_mode in [1,2]: # TS mode
            if isdeterP: # X -> X-T/F
                sibid = [k for k in self.G.iterNeighbors(begnode) if k != endnode]
                assert len(sibid) == 1, "not a deter p!!!"
                if (begnode, sibid[0]) in edge_p_dict:
                    return 1.0-edge_p_dict[(begnode, sibid[0])]
                else:
                    A = self.node_attrs[endnode].win
                    B = self.node_attrs[endnode].attempt - A
                    if B < 0:
                        logger.info("[debug]: win=%d, attempt=%d"%(A, self.node_attrs[endnode].attempt))
                        B = 0
                    p =  self.rnd.beta(1+A, 1+B)
                    return p
            else:       # X-T/F -> X
                P_visit = self.node_attrs[begnode].visit + self.node_attrs[begnode].attempt
                A = self.G.weight(begnode, endnode)
                B = P_visit - A
                p =  self.rnd.beta(1+A, 1+B)
                return p

    def free_space(self, PC_ids):
        PC_ids, extra = PC_ids.split("#")
        is_good, qid, pp_hash, treedepth, plen, conc_dir, tid, nid = [int(i) for i in PC_ids.replace(" ", "").strip("\n").split("-")]
        
        if qid == 1:
            logger.info("oldest tree to keep: %d"%(tid))
            counter = 0
            for i in range(0, tid):
                fname = "/outroot/tree1/id:%06d"%(i)
                if os.path.isfile(fname):
                    os.unlink(fname)
                    counter += 1
                    logger.info("delete %s"%(fname))
            logger.info("removed tree1 files with id < %d: %d"%(tid, counter))



    def run(self):
        newdata = ""
        with open("/tmp/pcpipe", "r") as fp:
            with open("/tmp/myfifo", "w") as fifo:
                while True:
                    newdata += fp.readline()
                    if len(newdata) == 0 or "@@" not in newdata:
                        continue
                    else:
                        index = newdata.find("@@")
                        while index >= 0:
                            record = newdata[:index]
                            newdata = newdata[index+2:]
                            index = newdata.find("@@")
                            if "END" not in record:
                                t1 = time.time()
                                self.add_one(record.replace("\n", " "))
                                self.update_cost += (time.time() - t1)
                            elif "ENDNEW" in record: # last pick resulted in a normal solving
                                self.ceq_decid.append(self.latest_node_choice)
                                self.node_attrs[self.latest_node_choice].attempt += 1
                                parentKey = self.node_attrs[self.latest_node_choice].parentKey
                                self.node_attrs[self.addr_nodeid[parentKey]].attempt += 1
                                self.solve_normal += 1
                                self.reset_for_new_trace()
                                # if random flipper, reset the record to include only the current trace
                                if self.s_mode == 4:
                                    # self.maxrecord = max(self.maxrecord, len(self.fifo_record))
                                    # fail safe; 
                                    self.fifo_record1 = self.fifo_record + self.fifo_record1
                                    self.fifo_record1 = self.fifo_record1[:self.maxrecord]
                                    # reset record 
                                    logger.info("leng: %d"%(len(self.fifo_record)))
                                    logger.info("leng1: %d"%(len(self.fifo_record1)))
                                    self.fifo_record = [] 
                                    # free disk space if not gonna pick that source seed for flipping 
                                    self.free_space(self.fifo_record1[-1])                                  
                                    
                            elif not ("UNSAT" in record or "DUP" in record or "FIN" in record):
                                self.reset_for_new_trace()
                            else: # prompt a new decision;
                                # initial corpus done, start scheduling
                                t1 = time.time()
                                
                                if self.s_mode == 4:                    # for random flipper
                                    if "UNSAT" in record:
                                        self.solve_unsat += 1
                                    if "DUP" in record:
                                        self.solve_duppp += 1                                    
                                    self.random_one(fifo)               
                                elif self.s_mode == 5:
                                    self.cfg_one(fifo)
                                else:                                   # for graph involved scheduler
                                    need_rerank = self.do_aftermath(record)
                                    self.sched_one(fifo, rerank=need_rerank)
                                
                                self.sched_cost += (time.time() - t1)

                                self.reset_for_new_trace()
                                if self.sched_round_all % 100 == 0:
                                    self.log_progress()


if __name__ == "__main__":
    args = parse_args()
    scheduler = Gsched(args.hybrid_mode, args.sched_mode)
    scheduler.run()