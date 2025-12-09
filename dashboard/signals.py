from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Transaction, GamificationProfile

@receiver(pre_delete, sender=Transaction)
def revoke_gamification_rewards(sender, instance, **kwargs):
    """
    If a transaction verified a quest, revoke the rewards if it's deleted.
    """
    if instance.verified_quest_id:
        # Find the user's profile
        try:
            profile = instance.user.gamification_profile
            # Deduct XP/Coins?
            # Issue: We don't know exactly how much XP was earned unless we look up the QuestLog.
            # But QuestLog stores quest_id.
            
            # Simple approach: Just log a warning or deduct a flat amount?
            # Better: Find the QuestLog entry.
            quest_log = instance.user.quest_logs.filter(quest_id=instance.verified_quest_id).first()
            
            if quest_log:
                profile.xp = max(0, profile.xp - quest_log.xp_earned)
                profile.coins = max(0, profile.coins - quest_log.coins_earned)
                profile.save()
                
                # Optional: Mark QuestLog as revoked or delete it?
                # Let's delete it so they can't re-exploit? Or keep it as "Revoked"?
                # Deleting it resets the "History".
                # But if they delete the transaction, they might be trying to re-do the quest?
                # If ID is daily unique, they can't re-do it easily if the day passed.
                
                # Decision: Just deduct rewards.
                print(f"REVOKED REWARDS for Quest {instance.verified_quest_id}: -{quest_log.xp_earned} XP")
                
        except Exception as e:
            print(f"Error revoking rewards: {e}")
