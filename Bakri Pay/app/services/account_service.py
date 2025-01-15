import logging
import uuid
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, Forbidden

from app import db
from app.models import Account, Transaction, User
from app.utils.validators import validate_amount

logger = logging.getLogger(__name__)


class AccountService:
    @staticmethod
    def get_user_accounts(user_id):
        """
        Get all accounts for a user
        Args:
            user_id: UUID of the user
        Returns:
            List of Account objects
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            return Account.query.filter_by(user_id=user_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch accounts for user {user_id}: {str(e)}")
            raise

    @staticmethod
    def get_account_details(user_id, account_id):
        """
        Get detailed account information with owner verification
        Args:
            user_id: UUID of requesting user
            account_id: UUID of the account
        Returns:
            Account object
        Raises:
            NotFound: If account doesn't exist
            Forbidden: If user doesn't own the account 
        """
        account = Account.query.get(account_id)
        
        if not account:
            raise NotFound(description='Account not found')
            
        if str(account.user_id) != str(user_id):
            logger.warning(f"Unauthorized account access attempt: {user_id} -> {account_id}")
            raise Forbidden(description='Unauthorized access to account')
            
        return account

    @staticmethod
    def get_account_balance(user_id, account_id):
        """
        Get balance for a specific account with ownership validation
        Args:
            user_id: UUID of the requesting user
            account_id: UUID of the account
        Returns:
            Decimal: Account balance
        Raises:
            NotFound: If account doesn't exist
            Forbidden: If user doesn't own the account
        """
        try:
            account = Account.query.get(account_id)

            if not account:
                raise NotFound(description='Account not found')

            if str(account.user_id) != str(user_id):
                raise Forbidden(description='Unauthorized access to account')

            return account.balance

        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch balance for account {account_id}: {str(e)}")
            raise

    @staticmethod
    def create_account(user_id):
        """
        Create a new virtual account for user
        Args:
            user_id: UUID of the user
        Returns:
            Account: The created account object
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Verify user exists
            user = User.query.get(user_id)
            if not user:
                raise NotFound(description='User not found')
            
            # Generate virtual account number
            account_number = f"SA{str(uuid.uuid4().int)[:10]}"

            account = Account(
                account_id=uuid.uuid4(),
                user_id=user_id,
                account_number=account_number,
                created_at=datetime.utcnow()
            )

            db.session.add(account)
            db.session.commit()

            logger.info(f"Created new account {account.account_id} for user {user_id}")
            return account

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to create account for user {user_id}: {str(e)}")
            raise

    @staticmethod
    def transfer_funds(source_account_id, target_account_id, amount, reference=""):
        """
        Transfer funds between accounts
        Args:
            source_account_id: UUID of source account
            target_account_id: UUID of target account
            amount: Decimal amount to transfer
            reference: Optional transfer reference
        Returns:
            Transaction: The created transaction record
        Raises:
            ValueError: If transfer is invalid
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate amount
            amount = validate_amount(amount)

            source = Account.query.get(source_account_id)
            target = Account.query.get(target_account_id)

            if not source or not target:
                raise NotFound(description="One or both accounts not found")

            if source.balance < amount:
                raise ValueError("Insufficient funds")

            # Perform transfer
            source.balance -= amount
            target.balance += amount

            # Create transaction record
            transaction = Transaction(
                transaction_id=uuid.uuid4(),
                from_account_id=source_account_id,
                to_account_id=target_account_id,
                amount=amount,
                transaction_type='transfer',
                reference=reference,
                status='completed',
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )

            db.session.add(transaction)
            db.session.commit()

            logger.info(f"Transferred {amount} from {source_account_id} to {target_account_id}")
            return transaction

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Transfer failed between {source_account_id} and {target_account_id}: {str(e)}")
            raise
