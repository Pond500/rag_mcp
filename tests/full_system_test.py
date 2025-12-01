"""
Full System Integration Test - Gun Law Dataset
Tests the complete RAG pipeline from document upload to chat
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.services import RAGService
from src.utils import get_logger

logger = get_logger(__name__)


class FullSystemTester:
    """Comprehensive system tester for RAG pipeline"""
    
    def __init__(self, data_folder: str, kb_name: str = "gun_law_test_full"):
        self.data_folder = Path(data_folder)
        self.kb_name = kb_name
        self.settings = get_settings()
        self.service = None
        self.test_results = {
            "kb_creation": None,
            "document_uploads": [],
            "search_tests": [],
            "chat_tests": [],
            "kb_list": None,
            "kb_deletion": None
        }
        
    def setup(self):
        """Initialize RAG service"""
        logger.info("🚀 Setting up RAG Service...")
        self.service = RAGService.from_settings(self.settings)
        logger.info("✅ RAG Service initialized")
        
    def test_1_create_kb(self):
        """Test 1: Create Knowledge Base"""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Create Knowledge Base")
        logger.info("="*80)
        
        try:
            result = self.service.create_kb(
                kb_name=self.kb_name,
                description="ทดสอบระบบด้วยข้อมูลงานอาวุธปืน - 16 เอกสาร",
                category="legal/gun_law"
            )
            
            self.test_results["kb_creation"] = result
            
            if result["success"]:
                logger.info(f"✅ KB Created: {self.kb_name}")
                logger.info(f"   Message: {result['message']}")
                return True
            else:
                logger.error(f"❌ Failed: {result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            self.test_results["kb_creation"] = {"success": False, "error": str(e)}
            return False
    
    def test_2_upload_documents(self):
        """Test 2: Upload All Documents"""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Upload Documents")
        logger.info("="*80)
        
        if not self.data_folder.exists():
            logger.error(f"❌ Folder not found: {self.data_folder}")
            return False
        
        # Get all .docx files
        docx_files = list(self.data_folder.glob("*.docx"))
        logger.info(f"📁 Found {len(docx_files)} DOCX files")
        
        success_count = 0
        fail_count = 0
        
        for idx, file_path in enumerate(docx_files, 1):
            logger.info(f"\n[{idx}/{len(docx_files)}] Uploading: {file_path.name}")
            
            try:
                start_time = time.time()
                
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                result = self.service.upload_document(
                    kb_name=self.kb_name,
                    filename=file_path.name,
                    file_content=file_content,
                    metadata={}
                )
                
                elapsed = time.time() - start_time
                
                upload_result = {
                    "filename": file_path.name,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "chunks": result.get("chunks_count", 0),  # Fixed key
                    "metadata": result.get("metadata", {}),
                    "elapsed_seconds": round(elapsed, 2)
                }
                
                self.test_results["document_uploads"].append(upload_result)
                
                if result.get("success"):
                    logger.info(f"   ✅ Success in {elapsed:.2f}s")
                    logger.info(f"   📄 Chunks: {result.get('chunks_count', 0)}")
                    logger.info(f"   🏷️  Type: {result.get('metadata', {}).get('doc_type', 'N/A')}")
                    success_count += 1
                else:
                    logger.error(f"   ❌ Failed: {result.get('message')}")
                    fail_count += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Exception: {e}")
                fail_count += 1
                self.test_results["document_uploads"].append({
                    "filename": file_path.name,
                    "success": False,
                    "error": str(e)
                })
        
        logger.info(f"\n📊 Upload Summary: {success_count} success, {fail_count} failed")
        return success_count > 0
    
    def test_3_search_queries(self):
        """Test 3: Search with Various Queries"""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Search Queries (Hybrid Search)")
        logger.info("="*80)
        
        test_queries = [
            {
                "query": "ขออนุญาตมีอาวุธปืนต้องทำอย่างไร",
                "description": "General gun permit question"
            },
            {
                "query": "เอกสารที่ต้องใช้ในการยื่นขออนุญาต",
                "description": "Required documents"
            },
            {
                "query": "ขอใบคู่มือประจำปืน",
                "description": "Gun manual request"
            },
            {
                "query": "การโอนใบอนุญาตอาวุธปืน",
                "description": "Transfer permit"
            },
            {
                "query": "ย้ายอาวุธปืนข้ามจังหวัด",
                "description": "Moving gun across provinces"
            }
        ]
        
        for idx, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            desc = test_case["description"]
            
            logger.info(f"\n[Query {idx}] {desc}")
            logger.info(f"Question: '{query}'")
            
            try:
                start_time = time.time()
                
                result = self.service.search(
                    query=query,
                    kb_name=self.kb_name,  # Single kb_name, not list
                    top_k=5,
                    use_routing=False,  # Direct search
                    use_reranking=True
                )
                
                elapsed = time.time() - start_time
                
                search_result = {
                    "query": query,
                    "description": desc,
                    "success": result.get("success", False),
                    "results_count": len(result.get("results", [])),
                    "elapsed_seconds": round(elapsed, 2),
                    "top_result": result.get("results", [{}])[0] if result.get("results") else None
                }
                
                self.test_results["search_tests"].append(search_result)
                
                if result.get("success"):
                    results = result.get("results", [])
                    logger.info(f"   ✅ Found {len(results)} results in {elapsed:.2f}s")
                    
                    if results:
                        top = results[0]
                        logger.info(f"   🏆 Top Result:")
                        logger.info(f"      Score: {top.get('score', 0):.4f}")
                        logger.info(f"      File: {top.get('metadata', {}).get('filename', 'N/A')}")
                        logger.info(f"      Text: {top.get('text', '')[:100]}...")
                else:
                    logger.error(f"   ❌ Search failed: {result.get('message')}")
                    
            except Exception as e:
                logger.error(f"   ❌ Exception: {e}")
                self.test_results["search_tests"].append({
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        return len([r for r in self.test_results["search_tests"] if r.get("success")]) > 0
    
    def test_4_chat_conversation(self):
        """Test 4: Multi-turn Chat Conversation"""
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Chat Conversation (with History)")
        logger.info("="*80)
        
        session_id = f"test_session_{int(time.time())}"
        
        conversation = [
            {
                "query": "ถ้าอยากมีปืนต้องทำอย่างไรบ้าง",
                "description": "Opening question"
            },
            {
                "query": "ต้องใช้เอกสารอะไรบ้าง",
                "description": "Follow-up on documents"
            },
            {
                "query": "ถ้าอยากย้ายปืนไปจังหวัดอื่นล่ะ",
                "description": "New topic - moving gun"
            },
            {
                "query": "แล้วถ้าหายหรือเสียหายต้องทำยังไง",
                "description": "Another topic - lost/damaged"
            }
        ]
        
        for idx, turn in enumerate(conversation, 1):
            query = turn["query"]
            desc = turn["description"]
            
            logger.info(f"\n[Turn {idx}] {desc}")
            logger.info(f"User: '{query}'")
            
            try:
                start_time = time.time()
                
                result = self.service.chat(
                    query=query,
                    session_id=session_id,
                    kb_name=self.kb_name,  # Single kb_name, not list
                    top_k=5,
                    use_routing=False,  # Direct search
                    use_reranking=True
                )
                
                elapsed = time.time() - start_time
                
                chat_result = {
                    "turn": idx,
                    "query": query,
                    "description": desc,
                    "success": result.get("success", False),
                    "answer": result.get("answer", ""),
                    "sources_count": len(result.get("sources", [])),
                    "elapsed_seconds": round(elapsed, 2)
                }
                
                self.test_results["chat_tests"].append(chat_result)
                
                if result.get("success"):
                    answer = result.get("answer", "")
                    sources = result.get("sources", [])
                    
                    logger.info(f"   ✅ Response in {elapsed:.2f}s")
                    logger.info(f"   🤖 Answer: {answer[:200]}...")
                    logger.info(f"   📚 Sources: {len(sources)} documents")
                else:
                    logger.error(f"   ❌ Chat failed: {result.get('message')}")
                    
            except Exception as e:
                logger.error(f"   ❌ Exception: {e}")
                self.test_results["chat_tests"].append({
                    "turn": idx,
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        return len([r for r in self.test_results["chat_tests"] if r.get("success")]) > 0
    
    def test_5_list_kbs(self):
        """Test 5: List All Knowledge Bases"""
        logger.info("\n" + "="*80)
        logger.info("TEST 5: List Knowledge Bases")
        logger.info("="*80)
        
        try:
            result = self.service.list_kbs()
            
            self.test_results["kb_list"] = result
            
            if result.get("success"):
                kbs = result.get("kbs", [])
                logger.info(f"✅ Found {len(kbs)} knowledge bases")
                
                for kb in kbs:
                    logger.info(f"   📚 {kb['kb_name']}")
                    logger.info(f"      Description: {kb.get('description', 'N/A')}")
                    logger.info(f"      Points: {kb.get('points_count', 0)}")
                    
                return True
            else:
                logger.error(f"❌ Failed: {result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return False
    
    def test_6_cleanup(self):
        """Test 6: Delete Test KB (Cleanup)"""
        logger.info("\n" + "="*80)
        logger.info("TEST 6: Cleanup - Delete Knowledge Base")
        logger.info("="*80)
        
        try:
            result = self.service.delete_kb(self.kb_name)
            
            self.test_results["kb_deletion"] = result
            
            if result.get("success"):
                logger.info(f"✅ KB Deleted: {self.kb_name}")
                return True
            else:
                logger.error(f"❌ Failed: {result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        logger.info("\n" + "="*80)
        logger.info("📊 FULL SYSTEM TEST SUMMARY")
        logger.info("="*80)
        
        # KB Creation
        kb_created = self.test_results["kb_creation"] and self.test_results["kb_creation"].get("success", False)
        logger.info(f"\n1️⃣  KB Creation: {'✅' if kb_created else '❌'}")
        
        # Document Uploads
        uploads = self.test_results["document_uploads"]
        upload_success = len([u for u in uploads if u.get("success", False)])
        upload_total = len(uploads)
        logger.info(f"\n2️⃣  Document Uploads: {upload_success}/{upload_total} ({'✅' if upload_success > 0 else '❌'})")
        
        if uploads:
            total_chunks = sum(u.get("chunks", 0) for u in uploads if u.get("success"))
            avg_time = sum(u.get("elapsed_seconds", 0) for u in uploads if u.get("success")) / max(upload_success, 1)
            logger.info(f"   📄 Total Chunks: {total_chunks}")
            logger.info(f"   ⏱️  Avg Time: {avg_time:.2f}s per document")
        
        # Search Tests
        searches = self.test_results["search_tests"]
        search_success = len([s for s in searches if s.get("success", False)])
        search_total = len(searches)
        logger.info(f"\n3️⃣  Search Queries: {search_success}/{search_total} ({'✅' if search_success > 0 else '❌'})")
        
        if searches and search_success > 0:
            avg_search_time = sum(s.get("elapsed_seconds", 0) for s in searches if s.get("success")) / search_success
            logger.info(f"   ⏱️  Avg Search Time: {avg_search_time:.2f}s")
        
        # Chat Tests
        chats = self.test_results["chat_tests"]
        chat_success = len([c for c in chats if c.get("success", False)])
        chat_total = len(chats)
        logger.info(f"\n4️⃣  Chat Turns: {chat_success}/{chat_total} ({'✅' if chat_success > 0 else '❌'})")
        
        if chats and chat_success > 0:
            avg_chat_time = sum(c.get("elapsed_seconds", 0) for c in chats if c.get("success")) / chat_success
            logger.info(f"   ⏱️  Avg Response Time: {avg_chat_time:.2f}s")
        
        # KB List
        kb_list = self.test_results["kb_list"]
        kb_list_success = kb_list and kb_list.get("success", False)
        logger.info(f"\n5️⃣  KB Listing: {'✅' if kb_list_success else '❌'}")
        
        # KB Deletion
        kb_deleted = self.test_results["kb_deletion"] and self.test_results["kb_deletion"].get("success", False)
        logger.info(f"\n6️⃣  KB Deletion: {'✅' if kb_deleted else '❌'}")
        
        # Overall
        all_passed = all([
            kb_created,
            upload_success > 0,
            search_success > 0,
            chat_success > 0,
            kb_list_success,
            kb_deleted
        ])
        
        logger.info("\n" + "="*80)
        if all_passed:
            logger.info("🎉 ALL TESTS PASSED! System is working perfectly!")
        else:
            logger.info("⚠️  Some tests failed. Check logs above for details.")
        logger.info("="*80 + "\n")
        
        return all_passed
    
    def run_all_tests(self):
        """Run complete test suite"""
        logger.info("\n" + "🎯"*40)
        logger.info("FULL SYSTEM INTEGRATION TEST - GUN LAW DATASET")
        logger.info("🎯"*40)
        
        self.setup()
        
        # Run all tests in sequence
        tests = [
            ("Create KB", self.test_1_create_kb),
            ("Upload Documents", self.test_2_upload_documents),
            ("Search Queries", self.test_3_search_queries),
            ("Chat Conversation", self.test_4_chat_conversation),
            ("List KBs", self.test_5_list_kbs),
            ("Cleanup", self.test_6_cleanup)
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                logger.error(f"❌ Test '{test_name}' crashed: {e}")
        
        # Print summary
        return self.print_summary()


def main():
    """Main entry point"""
    
    # Configuration
    DATA_FOLDER = "/Users/pond500/Downloads/1. งานอาวุธปืน"
    KB_NAME = "gun_law_test_full"
    
    # Run tests
    tester = FullSystemTester(DATA_FOLDER, KB_NAME)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
