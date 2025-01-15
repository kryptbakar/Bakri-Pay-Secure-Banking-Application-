import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, Forbidden

from app import db
from app.models import Transaction, Account, FraudAlert
from app.utils.validators import validate_amount

logger = logging.getLogger(__name__)


class TransactionService:

    @staticmethod
    def transfer_funds(user_id, from_account_id, to_account_id, amount, reference=""):
        """
        Transfer funds between accounts with validation and fraud checks
        Args:
            user_id: UUID of requesting user
            from_account_id: UUID of source account
            to_account_id: UUID of target account
            amount: Decimal amount to transfer
            reference: Optional transaction reference
        Returns:
            Transaction: The created transaction record
        Raises:
            Forbidden: If user doesn't own source account
            NotFound: If accounts don't exist
            ValueError: If transfer is invalid
        """
        try:
            # Validate amount
            amount = validate_amount(amount)

            # Verify source account ownership
            from_account = Account.query.filter_by(
                account_id=from_account_id,
                user_id=user_id
            ).first()

            if not from_account:
                raise Forbidden(description="Unauthorized access to source account")

            # Verify target account exists
            to_account = Account.query.get(to_account_id)
            if not to_account:
                raise NotFound(description="Recipient account not found")

            # Check sufficient balance
            if from_account.balance < amount:
                raise ValueError("Insufficient funds for transfer")

            # Check for self-transfer
            if from_account_id == to_account_id:
                raise ValueError("Cannot transfer to same account")

            # Create transaction record
            transaction = Transaction(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
                transaction_type='transfer',
                reference=reference,
                status='pending',
                created_at=datetime.utcnow()
            )

            # Update balances
            from_account.balance -= amount
            to_account.balance += amount
            transaction.status = 'completed'
            transaction.completed_at = datetime.utcnow()

            db.session.add(transaction)
            db.session.commit()

            # Fraud detection and prevention
            TransactionService._check_for_fraud(transaction)

            logger.info(
                f"Transfer of {amount} from {from_account_id} to {to_account_id} by user {user_id}"
            )
            return transaction

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Transfer failed between {from_account_id} and {to_account_id}: {str(e)}"
            )
            raise ValueError("Transaction processing failed")

    @staticmethod
    def create_deposit(user_id, account_id, amount, reference=""):
        """
        Create a deposit transaction
        Args:
            user_id: UUID of requesting user
            account_id: UUID of target account
            amount: Decimal deposit amount
            reference: Optional transaction reference
        Returns:
            Transaction: The created transaction record
        """
        try:
            amount = validate_amount(amount)

            # Verify account ownership
            account = Account.query.filter_by(
                account_id=account_id,
                user_id=user_id
            ).first()

            if not account:
                raise Forbidden(description="Unauthorized access to account")

            # Create deposit transaction
            transaction = Transaction(
                to_account_id=account_id,
                amount=amount,
                transaction_type='deposit',
                reference=reference,
                status='completed',
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )

            # Update balance
            account.balance += amount
            db.session.add(transaction)
            db.session.commit()

            logger.info(f"Deposit of {amount} to account {account_id}")
            return transaction

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Deposit failed to account {account_id}: {str(e)}")
            raise ValueError("Deposit processing failed")

    @staticmethod
    def get_transaction_history(user_id, account_id=None, limit=50, offset=0):
        """
        Get transaction history for user with pagination
        Args:
            user_id: UUID of user
            account_id: Optional specific account UUID
            limit: Max results to return
            offset: Pagination offset
        Returns:
            List[Transaction]: List of transaction records
        """
        try:
            base_query = Transaction.query.join(
                Account,
                (Transaction.from_account_id == Account.account_id) |
                (Transaction.to_account_id == Account.account_id)
            ).filter(Account.user_id == user_id)

            if account_id:
                # Verify account belongs to user
                if not Account.query.filter_by(
                        account_id=account_id,
                        user_id=user_id
                ).first():
                    raise Forbidden(description="Unauthorized access to account")

                base_query = base_query.filter(
                    (Transaction.from_account_id == account_id) |
                    (Transaction.to_account_id == account_id)
                )

            return base_query.order_by(
                Transaction.created_at.desc()
            ).limit(limit).offset(offset).all()

        except SQLAlchemyError as e:
            logger.error(f"Failed to get transactions for user {user_id}: {str(e)}")
            raise ValueError("Failed to retrieve transaction history")

    @staticmethod
    def get_transaction_details(user_id, transaction_id):
        """
        Get detailed transaction information
        Args:
            user_id: UUID of requesting user
            transaction_id: UUID of transaction
        Returns:
            Transaction: The transaction record
        Raises:
            Forbidden: If user doesn't have access
            NotFound: If transaction doesn't exist
        """
        try:
            transaction = db.session.query(Transaction).join(
                Account,
                (Transaction.from_account_id == Account.account_id) |
                (Transaction.to_account_id == Account.account_id)
            ).filter(
                Account.user_id == user_id,
                Transaction.transaction_id == transaction_id
            ).first()

            if not transaction:
                raise NotFound(description="Transaction not found")

            return transaction

        except SQLAlchemyError as e:
            logger.error(f"Failed to get transaction {transaction_id}: {str(e)}")
            raise ValueError("Failed to retrieve transaction details")

    @staticmethod
    def _check_for_fraud(transaction):
        """Internal fraud detection logic"""
        try:
            # Large amount check
            if transaction.amount > Decimal('50000'):
                alert = FraudAlert(
                    transaction_id=transaction.transaction_id,
                    reason='Large transaction amount',
                    action_taken='flagged',
                    created_at=datetime.utcnow()
                )
                db.session.add(alert)

            # Rapid successive transactions check
            recent_txns = Transaction.query.filter(
                Transaction.from_account_id == transaction.from_account_id,
                Transaction.created_at > datetime.utcnow() - timedelta(minutes=5)
            ).count()

            if recent_txns > 3:
                alert = FraudAlert(
                    transaction_id=transaction.transaction_id,
                    reason='High frequency transactions',
                    action_taken='flagged',
                    created_at=datetime.utcnow()
                )
                db.session.add(alert)

            db.session.commit()

        except Exception as e:
            logger.warning(f"Fraud detection failed for transaction {transaction.transaction_id}: {str(e)}")
            db.session.rollback()
