import pypdf
from transformers import pipeline
import re
from typing import Dict, List, Tuple
import numpy as np

class ManualAssistant:
    def __init__(self):
        """Initialize the Manual Assistant with necessary components"""
        # Initialize question-answering pipeline
        self.qa_pipeline = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad")
        self.manual_content = {}
        self.page_mapping = {}
        
    def load_manual(self, pdf_path: str) -> None:
        """
        Load and process a PDF manual
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        reader = pypdf.PdfReader(pdf_path)
        
        # Extract text from each page and maintain page mapping
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            
            # Store text with line numbers
            lines = text.split('\n')
            for line_num, line in enumerate(lines, 1):
                key = f"page_{page_num + 1}_line_{line_num}"
                self.manual_content[key] = line
                self.page_mapping[key] = (page_num + 1, line_num)
    
    def find_best_context(self, question: str, window_size: int = 5) -> Tuple[str, Dict]:
        """
        Find the most relevant context for a given question
        
        Args:
            question (str): User's question
            window_size (int): Number of lines to include in context window
            
        Returns:
            Tuple[str, Dict]: Context string and its metadata
        """
        best_score = -float('inf')
        best_context = ""
        best_metadata = {}
        
        # Create sliding windows of text
        for key in self.manual_content:
            current_page, current_line = self.page_mapping[key]
            
            # Build context window
            context_lines = []
            for i in range(-window_size // 2, window_size // 2 + 1):
                lookup_key = f"page_{current_page}_line_{current_line + i}"
                if lookup_key in self.manual_content:
                    context_lines.append(self.manual_content[lookup_key])
            
            context = " ".join(context_lines)
            
            # Skip empty contexts
            if not context.strip():
                continue
                
            # Use QA model to score relevance
            try:
                result = self.qa_pipeline(question=question, context=context)
                if result['score'] > best_score:
                    best_score = result['score']
                    best_context = context
                    best_metadata = {
                        'page': current_page,
                        'line': current_line,
                        'score': result['score']
                    }
            except Exception as e:
                continue
                
        return best_context, best_metadata
    
    def answer_question(self, question: str) -> str:
        """
        Answer a question about the manual
        
        Args:
            question (str): User's question
            
        Returns:
            str: Answer with page and line reference
        """
        if not self.manual_content:
            return "Please load a manual first."
            
        context, metadata = self.find_best_context(question)
        
        if not context:
            return "I couldn't find relevant information in the manual."
            
        # Get answer from QA pipeline
        result = self.qa_pipeline(question=question, context=context)
        
        # Format response with reference
        answer = f"{result['answer']} (Reference: Page {metadata['page']}, Line {metadata['line']})"
        
        return answer

def create_chat_interface():
    """Create a simple command-line interface for the manual assistant"""
    assistant = ManualAssistant()
    
    print("Welcome to Manual Assistant!")
    pdf_path = input("Please enter the path to your PDF manual: ")
    
    try:
        assistant.load_manual(pdf_path)
        print("Manual loaded successfully!")
        
        while True:
            question = input("\nAsk a question (or type 'quit' to exit): ")
            if question.lower() == 'quit':
                break
                
            answer = assistant.answer_question(question)
            print(f"\nAnswer: {answer}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    create_chat_interface()
