import pandas as pd
import json
from typing import Dict, List, Optional
import requests
from groq import Groq
from pdfconverter import *

class FinancialChatbot:
    """
    An agentic financial chatbot that helps with budgeting and expense tracking.
    Uses Grok AI API for intelligent analysis and recommendations.
    """
    
    def __init__(self, api_key: str, transactions_df: pd.DataFrame):
        """
        Initialize the chatbot with API key and transaction data.
        
        Args:
            api_key: Grok AI API key
            transactions_df: DataFrame with columns like 'amount', 'category', 'description', 'date'
        """
        self.api_key = api_key
        self.income = 0  # Income calculated from transactions
        self.transactions_df = self.categorize_transactions(transactions_df.copy())
        # Calculate income from transactions after categorization
        self._calculate_income_from_transactions()
        self.total_income = 0
        self.budget_goals = {
            'expenses': 0.70,  # 70% for needs
            'wants': 0.20,     # 20% for wants
            'savings': 0.10    # 10% for savings
        }
        self.conversation_history = []
        self.monthly_transactions = []
        
    def call_groq_api(self, messages: List[Dict], system_prompt: str = None) -> str:
        """
        Make API call to Groq AI.
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt to guide the model
            
        Returns:
            Model's response text
        """
        client = Groq(api_key=self.api_key)

        # Build messages list with system prompt and user messages
        api_messages = []
        if system_prompt:
            api_messages.append({
                "role": "system",
                "content": system_prompt,
            })
        # Add user/assistant messages from the conversation
        api_messages.extend(messages)

        chat_completion = client.chat.completions.create(
            messages=api_messages,
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content

    
    def set_income(self, income: float):
        """Set the total monthly income."""
        self.total_income = income
        print(f"Total income set to: ${income:,.2f}")
    
    def set_budget_goals(self, expenses: float = 0.70, wants: float = 0.20, savings: float = 0.10):
        """
        Set custom budget goals (should sum to 1.0).
        
        Args:
            expenses: Percentage for necessary expenses (0-1)
            wants: Percentage for wants/discretionary spending (0-1)
            savings: Percentage for savings (0-1)
        """
        total = expenses + wants + savings
        if abs(total - 1.0) > 0.01:
            print(f"⚠ Warning: Budget percentages sum to {total:.2f}, not 1.0. Normalizing...")
            expenses = expenses / total
            wants = wants / total
            savings = savings / total
        
        self.budget_goals = {
            'expenses': expenses,
            'wants': wants,
            'savings': savings
        }
        print(f"Budget goals set:")
        print(f"  - Expenses (Needs): {expenses*100:.1f}%")
        print(f"  - Wants: {wants*100:.1f}%")
        print(f"  - Savings: {savings*100:.1f}%")
    
    def calculate_budget_allocations(self) -> Dict:
        """Calculate dollar amounts for each budget category."""
        return {
            'expenses': self.total_income * self.budget_goals['expenses'],
            'wants': self.total_income * self.budget_goals['wants'],
            'savings': self.total_income * self.budget_goals['savings']
        }
    
    def categorize_transactions(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """Categorize transactions into expenses, wants and savings by making API calls to Groq"""
        for index, row in transactions_df.iterrows():
            system_prompt = """You are a transaction classifier. Classify transactions into:
            - category: specific category (e.g., 'Groceries', 'Entertainment', 'Rent', 'Salary', 'Payroll', etc.)
            - category_type: one of 'income' (money coming in like salary, payroll, deposits), 'expenses' (needs), 'wants' (discretionary), or 'savings' (investments/savings)
            
            Respond ONLY with a JSON object like: {"category": "Groceries", "category_type": "expenses"} or {"category": "Salary", "category_type": "income"}"""
            user_message = f"""Classify this transaction:
            Description: {row.get('transaction_description', row.get('description', ''))}
            Amount: ${row.get('transaction_amount', row.get('amount', 0)):.2f}

            Respond with JSON only."""
            messages = [{"role": "user", "content": user_message}]
            response = self.call_groq_api(messages, system_prompt)
            print(response)
            try:
                response_json = json.loads(response.strip().replace("```json", "").replace("```", "").strip())
            except:
                response_json = {}
            transactions_df.at[index, 'category'] = response_json.get('category', 'Uncategorized')
            transactions_df.at[index, 'category_type'] = response_json.get('category_type', 'expenses')
        return transactions_df
    
    def _calculate_income_from_transactions(self):
        """Calculate total income from transactions categorized as 'income'."""
        income_total = 0
        for _, row in self.transactions_df.iterrows():
            if row.get('category_type') == 'income':
                amount = row.get('transaction_amount', row.get('amount', 0))
                if amount > 0:  # Only count positive amounts as income
                    income_total += amount
        self.income = income_total
        print(f"💰 Calculated income from transactions: ${self.income:,.2f}")
    
    def analyze_current_spending(self) -> Dict:
        """Analyze current spending from transactions."""
        # Combine historical and new transactions
        all_transactions = self.transactions_df.copy()
        
        if self.monthly_transactions:
            new_df = pd.DataFrame(self.monthly_transactions)
            all_transactions = pd.concat([all_transactions, new_df], ignore_index=True)
        
        # Calculate spending by category type
        # Assuming transactions have a 'category_type' column: 'expenses', 'wants', or 'savings'
        # If not, we'll need to map categories
        spending = {
            'expenses': 0,
            'wants': 0,
            'savings': 0
        }
        
        category_breakdown = {}
        
        for _, row in all_transactions.iterrows():
            category_type = row.get('category_type', 'expenses')  # default to expenses
            
            # Skip income transactions - they're tracked separately
            if category_type == 'income':
                continue
            
            amount = abs(row.get('transaction_amount', row.get('amount', 0)))
            spending[category_type] = spending.get(category_type, 0) + amount
            category_breakdown[row.get('category', 'Uncategorized')] = category_breakdown.get(row.get('category', 'Uncategorized'), 0) + amount
        
        print(category_breakdown)
        print(spending)
        print(sum(spending.values()))
        return {
            'spending': spending,
            'category_breakdown': category_breakdown,
            'total_spent': sum(spending.values())
        }
    
    def get_initial_analysis(self) -> str:
        """Generate initial budget analysis and recommendations."""
        budget = self.calculate_budget_allocations()
        current = self.analyze_current_spending()
        
        system_prompt = """You are a helpful financial advisor chatbot. Analyze the user's spending 
        and provide clear, actionable advice. Be encouraging but honest about areas for improvement.
        IMPORTANT: For savings, exceeding the goal is excellent and should be praised! Savings above 
        the target is a positive achievement, not overspending. Format your response in a clear, conversational way."""
        
        analysis_data = {
            'total_income': self.total_income,
            'budget_goals': self.budget_goals,
            'budget_allocations': budget,
            'current_spending': current['spending'],
            'category_breakdown': current['category_breakdown'],
            'total_spent': current['total_spent']
        }
        
        user_message = f"""Please analyze my budget situation:

            Income from transactions: ${self.income:,.2f}
            Budget income (user-set): ${self.total_income:,.2f}

            Budget Goals:
            - Expenses (Needs): {self.budget_goals['expenses']*100:.0f}% = ${budget['expenses']:,.2f}
            - Wants: {self.budget_goals['wants']*100:.0f}% = ${budget['wants']:,.2f}
            - Savings: {self.budget_goals['savings']*100:.0f}% = ${budget['savings']:,.2f}

            Current Spending:
            - Expenses: ${current['spending']['expenses']:,.2f}
            - Wants: ${current['spending']['wants']:,.2f}
            - Savings: ${current['spending']['savings']:,.2f}
            Total Spent: ${current['total_spent']:,.2f}

            Category Breakdown:
            {json.dumps(current['category_breakdown'], indent=2)}

            Please provide:
            1. An overview of my spending vs budget
            2. My income from the transactions
            3. Which categories I'm overspending in (note: exceeding savings goal is good, not overspending)
            4. Specific suggestions on where to cut back
            5. Remaining budget for each category this month (for savings, show if I've exceeded the goal)"""

        messages = [{"role": "user", "content": user_message}]
        self.conversation_history.append({"role": "user", "content": user_message})
        
        response = self.call_groq_api(messages, system_prompt)
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def add_transaction(self, amount: float, description: str, category: str = None, 
                       category_type: str = None) -> str:
        """
        Add a new transaction and get updated analysis.
        
        Args:
            amount: Transaction amount (positive)
            description: Description of the transaction
            category: Optional category name
            category_type: Optional category type ('expenses', 'wants', or 'savings')
            
        Returns:
            Updated budget analysis
        """
        # If category/category_type not provided, ask Grok to classify
        if not category or not category_type:
            classification = self._classify_transaction(description, amount)
            if not category:
                category = classification.get('category', 'Uncategorized')
            if not category_type:
                category_type = classification.get('category_type', 'expenses')
        
        # Add transaction to monthly list
        transaction = {
            'amount': amount,
            'description': description,
            'category': category,
            'category_type': category_type,
            'date': pd.Timestamp.now()
        }
        self.monthly_transactions.append(transaction)
        
        # Get updated analysis
        return self._get_updated_analysis(transaction)
    
    def _classify_transaction(self, description: str, amount: float) -> Dict:
        """Use Grok to classify a transaction."""
        system_prompt = """You are a transaction classifier. Classify transactions into:
        - category: specific category (e.g., 'Groceries', 'Entertainment', 'Rent', etc.)
        - category_type: one of 'expenses' (needs), 'wants' (discretionary), or 'savings' (investments/savings)
        
        Respond ONLY with a JSON object like: {"category": "Groceries", "category_type": "expenses"}"""
        
        user_message = f"""Classify this transaction:
Description: {description}
Amount: ${amount:.2f}

Respond with JSON only."""

        messages = [{"role": "user", "content": user_message}]
        response = self.call_groq_api(messages, system_prompt)
        
        try:
            # Extract JSON from response (in case model adds extra text)
            response = response.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except:
            return {'category': 'Uncategorized', 'category_type': 'expenses'}
    
    def _get_updated_analysis(self, new_transaction: Dict) -> str:
        """Get updated budget analysis after adding a transaction."""
        budget = self.calculate_budget_allocations()
        current = self.analyze_current_spending()
        
        remaining = {
            'expenses': budget['expenses'] - current['spending']['expenses'],
            'wants': budget['wants'] - current['spending']['wants'],
            'savings': current['spending']['savings'] - budget['savings']  # Positive when exceeding goal
        }
        
        user_message = f"""I just added a new transaction:
- Amount: ${new_transaction['amount']:.2f}
- Description: {new_transaction['description']}
- Category: {new_transaction['category']} ({new_transaction['category_type']})

Updated Spending:
- Expenses: ${current['spending']['expenses']:,.2f} / ${budget['expenses']:,.2f} (Remaining: ${remaining['expenses']:,.2f})
- Wants: ${current['spending']['wants']:,.2f} / ${budget['wants']:,.2f} (Remaining: ${remaining['wants']:,.2f})
- Savings: ${current['spending']['savings']:,.2f} / ${budget['savings']:,.2f} ({'Exceeded goal by' if remaining['savings'] > 0 else 'Remaining'}: ${abs(remaining['savings']):,.2f})

Total Spent: ${current['total_spent']:,.2f} / ${self.total_income:,.2f}

Please:
1. Acknowledge the transaction
2. Update me on my remaining budget for the month (for savings, celebrate if I've exceeded the goal!)
3. Let me know if I'm on track or need to adjust spending
4. Give specific advice if I'm overspending in any category (remember: exceeding savings goal is excellent, not overspending)"""

        self.conversation_history.append({"role": "user", "content": user_message})
        
        system_prompt = """You are a helpful financial advisor. Provide brief, actionable updates 
        when users add transactions. Be encouraging when they're on track and gently firm when 
        they're overspending. IMPORTANT: For savings transactions, exceeding the savings goal is 
        excellent and should be praised! Savings above the target is a positive achievement."""
        
        response = self.call_groq_api(self.conversation_history, system_prompt)
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def chat(self, message: str) -> str:
        """
        Continue the conversation with custom questions.
        
        Args:
            message: User's message
            
        Returns:
            Chatbot's response
        """
        self.conversation_history.append({"role": "user", "content": message})
        
        system_prompt = """You are a helpful financial advisor chatbot. Answer questions about 
        budgeting, spending, and financial planning. Be supportive and provide practical advice."""
        
        response = self.call_groq_api(self.conversation_history, system_prompt)
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def get_summary(self) -> Dict:
        """Get a summary of the current budget status."""
        budget = self.calculate_budget_allocations()
        current = self.analyze_current_spending()
        
        remaining = {
            'expenses': budget['expenses'] - current['spending']['expenses'],
            'wants': budget['wants'] - current['spending']['wants'],
            'savings': current['spending']['savings'] - budget['savings']  # Positive when exceeding goal
        }
        
        return {
            'total_income': self.total_income,
            'budget_allocations': budget,
            'current_spending': current['spending'],
            'remaining_budget': remaining,
            'total_spent': current['total_spent'],
            'total_remaining': self.total_income - current['total_spent'],
            'category_breakdown': current['category_breakdown'],
            'transactions_count': len(self.transactions_df) + len(self.monthly_transactions)
        }
    
    def print_summary(self):
        """Print a formatted summary of the budget status."""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("BUDGET SUMMARY")
        print("="*60)
        print(f"\nTotal Income: ${summary['total_income']:,.2f}")
        print(f"Total Spent: ${summary['total_spent']:,.2f}")
        print(f"Remaining: ${summary['total_remaining']:,.2f}")
        print(f"\n{'Category':<20} {'Budget':<15} {'Spent':<15} {'Remaining':<15}")
        print("-"*60)
        
        for category in ['expenses', 'wants', 'savings']:
            budget = summary['budget_allocations'][category]
            spent = summary['current_spending'][category]
            remaining = summary['remaining_budget'][category]
            if category == 'savings':
                # For savings, positive remaining means exceeded goal (good!)
                status = "🎉" if remaining > 0 else ("✓" if remaining >= 0 else "⚠")
                remaining_display = remaining  # Already shows exceeded amount as positive
            else:
                # For expenses and wants, positive remaining is good
                status = "✓" if remaining >= 0 else "⚠"
                remaining_display = remaining
            print(f"{category.capitalize():<20} ${budget:>12,.2f} ${spent:>12,.2f} ${remaining_display:>12,.2f} {status}")
        
        print("\n" + "="*60)
        print(f"Total Transactions: {summary['transactions_count']}")
        print("="*60 + "\n")


# Example usage function for notebook
def example_usage():
    """
    Example of how to use the FinancialChatbot in a notebook.
    """
    # Sample transaction data
    sample_data = {
        'amount': [1200, 45, 150, 80, 200, 35, 500],
        'description': ['Rent', 'Groceries', 'Dinner out', 'Gas', 'Shopping', 'Coffee', 'Investment'],
        'category': ['Housing', 'Food', 'Dining', 'Transportation', 'Shopping', 'Dining', 'Savings'],
        'category_type': ['expenses', 'expenses', 'wants', 'expenses', 'wants', 'wants', 'savings']
    }
    
    df = pd.DataFrame(sample_data)
    
    # Initialize chatbot (replace with your actual API key)
    API_KEY = "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"
    chatbot = FinancialChatbot(API_KEY, df)
    
    # Step 1: Set income
    chatbot.set_income(5000)
    
    # Step 2: Set budget goals (optional - uses defaults if not called)
    chatbot.set_budget_goals(expenses=0.70, wants=0.20, savings=0.10)
    
    # Step 3: Get initial analysis
    print("\n" + "="*60)
    print("INITIAL ANALYSIS")
    print("="*60)
    #analysis = chatbot.get_initial_analysis()
    ##print(analysis)
    
    # Step 4: Add new transactions interactively
    print("\n" + "="*60)
    print("ADDING NEW TRANSACTION")
    print("="*60)
    response = chatbot.add_transaction(75, "Bought new shoes", "Shopping", "wants")
    print(response)
    
    # Step 5: Add another transaction (auto-classify)
    print("\n" + "="*60)
    print("ADDING ANOTHER TRANSACTION (AUTO-CLASSIFIED)")
    print("="*60)
    response = chatbot.add_transaction(120, "Dinner at Italian restaurant")
    print(response)
    
    # Step 6: Ask custom questions
    print("\n" + "="*60)
    print("CUSTOM QUESTION")
    print("="*60)
    response = chatbot.chat("Should I go out for drinks this weekend if it costs $50?")
    print(response)
    
    # Step 7: Print summary
    chatbot.print_summary()
    
    return chatbot


if __name__ == "__main__":
    print("Financial Chatbot Module Loaded!")
    print("Use example_usage() to see a demo, or create your own instance.")
    API_KEY = "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"
    test_df = load_transactions_from_file(r"C:\Users\Mitsy\Downloads\bank_statement_ex.xlsx")
    test_chatbot = FinancialChatbot(API_KEY, test_df)
    test_chatbot.set_budget_goals(expenses=0.70, wants=0.20, savings=0.10)
    test_chatbot.get_initial_analysis()
    test_chatbot.print_summary()