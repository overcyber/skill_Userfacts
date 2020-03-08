from core.base.model.AliceSkill import AliceSkill
from core.base.model.Intent import Intent
from core.dialog.model.DialogSession import DialogSession


class Userfacts(AliceSkill):
	"""
	Author: Psychokiller1888
	Description: Now alice can remember things about you if you teach her!
	"""

	_INTENT_GET_USER_FACT    = Intent('GetUserFact')
	_INTENT_DELETE_ALL_FACTS = Intent('DeleteAllUserFacts')
	_INTENT_USER_ANSWER      = Intent('UserRandomAnswer')
	_INTENT_ANSWER_YES_OR_NO = Intent('AnswerYesOrNo')

	DATABASE = {
		'facts': [
			'id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE',
			'username TEXT NOT NULL',
			'fact TEXT NOT NULL',
			'value TEXT NOT NULL'
		]
	}

	def __init__(self):
		self._INTENTS = [
			(self._INTENT_GET_USER_FACT, self.getUserFact),
			(self._INTENT_USER_ANSWER, self.getUserFact)
		]

		super().__init__(supportedIntents=self._INTENTS, databaseSchema=self.DATABASE)


	def getUserFact(self, session: DialogSession, **_kwargs):
		if not session.user:
			self.endDialog(sessionId=session.sessionId, text=self.randomTalk(text='dontKnowYou'))

		slots = session.slotsAsObjects
		if not slots['RandomWord']:
			self.endDialog(sessionId=session.sessionId, text=self.TalkManager.randomTalk('notUnderstood', skill='system'))

		if len(slots['RandomWord']) == 1:
			fact = session.slotRawValue('RandomWord')
		else:
			fact = ''
			for slot in slots:
				if not slot:
					continue

				fact += f' {slot.value["value"]}'

		answer = self.databaseFetch(
			tableName='facts',
			query='SELECT value FROM :__table__ WHERE username = :username AND fact = :fact',
			values={
				'username': session.user,
				'fact'    : fact
			}
		)

		if not answer:
			self.continueDialog(
				sessionId=session.sessionId,
				text=self.randomTalk(text='noResult'),
				intentFilter=[self._INTENT_USER_ANSWER],
				probabilityThreshold=0.1,
				currentDialogState='answeringFactValue'
			)
		else:
			self.endDialog(
				sessionId=session.sessionId,
				text=self.randomTalk(text='fact', replace=[answer['value']])
			)
