import logging
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, Forbidden

from app import db
from app.models import Card, Account
from app.utils.validators import validate_card_expiry

logger = logging.getLogger(__name__)


class CardService:

    @staticmethod
    def create_virtual_card(user_id, account_id):
        """
        Create a new virtual card for an account
        Args:
            user_id: UUID of requesting user
            account_id: UUID of the account
        Returns:
            Card: The created card object
        Raises:
            Forbidden: If user doesn't own the account
            NotFound: If account doesn't exist
        """
        try:
            # Verify account ownership
            account = Account.query.filter_by(
                account_id=account_id,
                user_id=user_id
            ).first()

            if not account:
                raise Forbidden(description="Unauthorized access to account")

            # Generate card details
            card_number = CardService._generate_card_number()
            expiry_date = (datetime.utcnow() + timedelta(days=365 * 3)).strftime('%m/%y')  # 3 years validity
            cvv = f"{random.randint(0, 999):03d}"

            card = Card(
                card_id=uuid.uuid4(),
                account_id=account_id,
                card_number=card_number,
                expiry_date=expiry_date,
                cvv_hash=CardService._hash_cvv(cvv),
                is_virtual=True,
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.session.add(card)
            db.session.commit()

            logger.info(f"Created virtual card {card.card_id} for account {account_id}")

            # Return masked card details
            return {
                'card_id': str(card.card_id),
                'last_four': card_number[-4:],
                'expiry_date': expiry_date,
                'is_virtual': True,
                'is_active': True
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to create virtual card: {str(e)}")
            raise ValueError("Card creation failed")

    @staticmethod
    def request_physical_card(user_id, account_id, delivery_address):
        """
        Request a physical card
        Args:
            user_id: UUID of requesting user
            account_id: UUID of the account
            delivery_address: Dict of address details
        Returns:
            Dict: Card request details
        """
        try:
            # Verify account ownership
            account = Account.query.filter_by(
                account_id=account_id,
                user_id=user_id
            ).first()

            if not account:
                raise Forbidden(description="Unauthorized access to account")

            # Generate card details
            card_number = CardService._generate_card_number()
            expiry_date = (datetime.utcnow() + timedelta(days=365 * 3)).strftime('%m/%y')
            cvv = f"{random.randint(0, 999):03d}"

            card = Card(
                card_id=uuid.uuid4(),
                account_id=account_id,
                card_number=card_number,
                expiry_date=expiry_date,
                cvv_hash=CardService._hash_cvv(cvv),
                is_virtual=False,
                is_active=False,  # Inactive until activated
                delivery_address=delivery_address,
                created_at=datetime.utcnow()
            )

            db.session.add(card)
            db.session.commit()

            logger.info(f"Requested physical card {card.card_id} for account {account_id}")

            return {
                'card_id': str(card.card_id),
                'status': 'requested',
                'estimated_delivery': (datetime.utcnow() + timedelta(days=7)).isoformat()
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to request physical card: {str(e)}")
            raise ValueError("Card request failed")

    @staticmethod
    def get_user_cards(user_id, account_id=None):
        """
        Get all cards for a user
        Args:
            user_id: UUID of the user
            account_id: Optional specific account UUID
        Returns:
            List[Dict]: List of card details
        """
        try:
            query = db.session.query(Card).join(Account).filter(Account.user_id == user_id)

            if account_id:
                # Verify account ownership
                if not Account.query.filter_by(
                        account_id=account_id,
                        user_id=user_id
                ).first():
                    raise Forbidden(description="Unauthorized access to account")

                query = query.filter(Card.account_id == account_id)

            cards = query.order_by(Card.created_at.desc()).all()

            return [{
                'card_id': str(card.card_id),
                'last_four': card.card_number[-4:],
                'expiry_date': card.expiry_date,
                'is_virtual': card.is_virtual,
                'is_active': card.is_active,
                'created_at': card.created_at.isoformat()
            } for card in cards]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get cards for user {user_id}: {str(e)}")
            raise ValueError("Failed to retrieve cards")

    @staticmethod
    def toggle_card_status(user_id, card_id, activate=True):
        """
        Activate or deactivate a card
        Args:
            user_id: UUID of requesting user
            card_id: UUID of the card
            activate: Boolean to activate/deactivate
        Returns:
            Dict: Updated card status
        """
        try:
            card = Card.query.join(Account).filter(
                Card.card_id == card_id,
                Account.user_id == user_id
            ).first()

            if not card:
                raise NotFound(description="Card not found or unauthorized")

            card.is_active = activate
            db.session.commit()

            logger.info(f"{'Activated' if activate else 'Deactivated'} card {card_id}")

            return {
                'card_id': str(card.card_id),
                'is_active': card.is_active,
                'status': 'active' if card.is_active else 'inactive'
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to toggle card status: {str(e)}")
            raise ValueError("Card status update failed")

    @staticmethod
    def report_card_lost_or_stolen(user_id, card_id):
        """
        Report a card as lost/stolen and issue replacement
        Args:
            user_id: UUID of requesting user
            card_id: UUID of the card
        Returns:
            Dict: Replacement card details
        """
        try:
            # Get and deactivate old card
            card = Card.query.join(Account).filter(
                Card.card_id == card_id,
                Account.user_id == user_id
            ).first()

            if not card:
                raise NotFound(description="Card not found or unauthorized")

            card.is_active = False
            card.deactivated_at = datetime.utcnow()
            card.deactivation_reason = 'lost_or_stolen'

            # Create replacement card
            if card.is_virtual:
                replacement = CardService.create_virtual_card(user_id, card.account_id)
            else:
                replacement = CardService.request_physical_card(
                    user_id,
                    card.account_id,
                    card.delivery_address
                )

            db.session.commit()
            logger.info(f"Replaced lost/stolen card {card_id} with {replacement['card_id']}")

            return {
                'old_card_id': str(card.card_id),
                'replacement_card': replacement,
                'message': 'Card reported and replacement issued'
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to report card lost/stolen: {str(e)}")
            raise ValueError("Card replacement failed")

    @staticmethod
    def _generate_card_number():
        """Generate a random valid card number using Luhn algorithm"""
        # Start with bank's IIN (Issuer Identification Number)
        prefix = '4242'

        # Generate 11 random digits
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(11)])

        # Combine and calculate check digit
        partial_number = prefix + random_digits
        check_digit = CardService._luhn_check_digit(partial_number)

        return partial_number + str(check_digit)

    @staticmethod
    def _luhn_check_digit(partial_number):
        """Calculate Luhn check digit for card number validation"""
        total = 0
        for i, digit in enumerate(reversed(partial_number)):
            num = int(digit)
            if i % 2 == 0:
                num *= 2
                if num > 9:
                    num = (num // 10) + (num % 10)
            total += num
        return (10 - (total % 10)) % 10

    @staticmethod
    def _hash_cvv(cvv):
        """Securely hash CVV for storage"""
        # In a real application, use proper cryptographic hashing
        from app.utils.security import hash_pin
        return hash_pin(cvv)  # Reuse our secure PIN hashing
