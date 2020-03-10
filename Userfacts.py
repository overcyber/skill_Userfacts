from core.base.model.AliceSkill import AliceSkill
from core.base.model.Intent import Intent
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class Userfacts(AliceSkill):
	"""
	Author: Psychokiller1888
	Description: Now alice can remember things about you if you teach her!
	"""

	_INTENT_GET_USER_FACT = Intent('GetUserFact')
	_INTENT_DELETE_ALL_FACTS = Intent('DeleteAllUserFacts')
	_INTENT_USER_ANSWER = Intent('UserRandomAnswer', isProtected=True)
	_INTENT_ANSWER_YES_OR_NO = Intent('AnswerYesOrNo', isProtected=True)
	_INTENT_SPELL_WORD = Intent('SpellWord', isProtected=True)

	DATABASE = {
		'facts': [
			'username TEXT NOT NULL',
			'fact TEXT NOT NULL',
			'value TEXT NOT NULL',
			'UNIQUE (username, fact)'
		]
	}

	def __init__(self):
		self._INTENTS = [
			(self._INTENT_GET_USER_FACT, self.getUserFact),
			self._INTENT_USER_ANSWER,
			self._INTENT_SPELL_WORD,
			self._INTENT_ANSWER_YES_OR_NO,
			(self._INTENT_DELETE_ALL_FACTS, self.deleteAll)
		]

		self._INTENT_USER_ANSWER.dialogMapping = {
			'answeringFactValue': self.setUserFact
		}

		self._INTENT_SPELL_WORD.dialogMapping = {
			'answeringFactValue': self.setUserFact
		}

		self._INTENT_ANSWER_YES_OR_NO.dialogMapping = {
			'confirmingFactValue': self.userFactValueConfirmed,
			'confirmingDeleteAll': self.deleteAllConfirmed
		}

		self._previousFact = ''

		super().__init__(supportedIntents=self._INTENTS, databaseSchema=self.DATABASE)


	def onContextSensitiveDelete(self, session: DialogSession):
		if not self.isContextForMe(session):
			return

		# noinspection SqlResolve
		self.DatabaseManager.delete(
			tableName='facts',
			callerName=self.name,
			query='DELETE FROM :__table__ WHERE username = :user AND fact = :fact',
			values={
				'user': session.user,
				'fact': self._previousFact
			}
		)

		self.endDialog(sessionId=session.sessionId, text=self.randomTalk(text='okDeleted'))


	def onContextSensitiveEdit(self, session: DialogSession):
		if not self.isContextForMe(session):
			return

		self.continueDialog(
			sessionId=session.sessionId,
			text=self.randomTalk(text='whatIsItNew'),
			intentFilter=[self._INTENT_USER_ANSWER, self._INTENT_SPELL_WORD],
			probabilityThreshold=0.01,
			currentDialogState='answeringFactValue',
			customData={
				'skill': self.name,
				'fact' : self._previousFact
			}
		)


	def isContextForMe(self, session: DialogSession) -> bool:
		if not self._previousFact:
			return False

		if not session.user or session.user == constants.UNKNOWN_USER:
			self.endDialog(sessionId=session.sessionId, text=self.randomTalk(text='dontKnowYou'))
			return False

		contextSkill = self.SkillManager.getSkillInstance(skillName='ContextSensitive', silent=True)
		lastSession = contextSkill.lastSession()
		if not lastSession or str(self._INTENT_GET_USER_FACT) not in lastSession.intentHistory:
			return False

		if lastSession.customData['user'] != session.user:
			self.endDialog(sessionId=session.sessionId, text=self.randomTalk(text='notUpToYou'))
			return False

		return True


	def deleteAll(self, session: DialogSession):
		if not session.user or session.user == constants.UNKNOWN_USER:
			self.endDialog(sessionId=session.sessionId, text=self.randomTalk(text='dontKnowYou'))

		self.continueDialog(
			sessionId=session.sessionId,
			text=self.randomTalk(text='confirmDeleteAll'),
			intentFilter=[self._INTENT_ANSWER_YES_OR_NO],
			probabilityThreshold=0.1,
			currentDialogState='confirmingDeleteAll'
		)


	def deleteAllConfirmed(self, session: DialogSession):
		if self.Commons.isYes(session):
			# noinspection SqlResolve
			self.DatabaseManager.delete(
				tableName='facts',
				callerName=self.name,
				query='DELETE FROM :__table__ WHERE username = :user',
				values={
					'user': session.user
				}
			)

			self.endDialog(
				sessionId=session.sessionId,
				text=self.randomTalk(text='okDeletedAll')
			)
		else:
			self.endDialog(sessionId=session.sessionId, text=self.randomTalk(text='deleteAllDenied'))


	def setUserFact(self, session: DialogSession) -> bool:
		if session.intentName == self._INTENT_USER_ANSWER:
			value = session.slots['RandomWord'].lower()
		else:
			value = ''.join([slot.value['value'] for slot in session.slotsAsObjects['Letters']])

		self.continueDialog(
			sessionId=session.sessionId,
			text=self.randomTalk(text='factConfirmValue', replace=[value]),
			intentFilter=[self._INTENT_ANSWER_YES_OR_NO],
			probabilityThreshold=0.1,
			currentDialogState='confirmingFactValue',
			customData={
				'fact' : session.customData['fact'],
				'value': value
			}
		)
		return True


	def userFactValueConfirmed(self, session: DialogSession):
		if self.Commons.isYes(session):
			# noinspection SqlResolve
			self.DatabaseManager.replace(
				tableName='facts',
				query='REPLACE INTO :__table__ (username, fact, value) VALUES (:username, :fact, :value)',
				callerName=self.name,
				values={
					'username': session.user,
					'fact'    : session.customData['fact'],
					'value'   : session.customData['value']
				}
			)

			self.endDialog(
				sessionId=session.sessionId,
				text=self.randomTalk(text='confirmValueSaved')
			)
		else:
			self.continueDialog(
				sessionId=session.sessionId,
				text=self.randomTalk(text='valueNotCorrect'),
				intentFilter=[self._INTENT_USER_ANSWER, self._INTENT_SPELL_WORD],
				probabilityThreshold=0.01,
				currentDialogState='answeringFactValue',
				customData={
					'skill': self.name,
					'fact' : session.customData['fact']
				}
			)


	def getUserFact(self, session: DialogSession, **_kwargs):
		if not session.user or session.user == constants.UNKNOWN_USER:
			self.endDialog(sessionId=session.sessionId, text=self.randomTalk(text='dontKnowYou'))

		slots = session.slotsAsObjects
		if not slots['Fact']:
			self.endDialog(sessionId=session.sessionId, text=self.TalkManager.randomTalk('notUnderstood', skill='system'))

		if len(slots['Fact']) == 1:
			fact = session.slotRawValue('Fact').lower()
		else:
			facts = [slot.value['value'].lower() for slot in session.slotsAsObjects.get('Fact', list())]
			fact = ' '.join(facts)

		# noinspection SqlResolve
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
				intentFilter=[self._INTENT_USER_ANSWER, self._INTENT_SPELL_WORD],
				probabilityThreshold=0.01,
				currentDialogState='answeringFactValue',
				customData={
					'fact' : fact
				}
			)
		else:
			self._previousFact = fact
			self.endDialog(
				sessionId=session.sessionId,
				text=self.randomTalk(text='fact', replace=[fact, answer['value']])
			)
