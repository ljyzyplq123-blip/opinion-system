"""
数据库模型定义 - 8张表
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    avatar = db.Column(db.String(200), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    monitored_sources = db.relationship('MonitoredSource', backref='user', lazy='dynamic',
                                        cascade='all, delete-orphan')
    monitored_keywords = db.relationship('MonitoredKeyword', backref='user', lazy='dynamic',
                                         cascade='all, delete-orphan')
    qa_history = db.relationship('QAHistory', backref='user', lazy='dynamic',
                                 cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class MonitoredSource(db.Model):
    """监控源配置表"""
    __tablename__ = 'monitored_sources'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform_name = db.Column(db.String(100), nullable=False)
    platform_url = db.Column(db.String(500), nullable=False)
    source_type = db.Column(db.String(50), default='news')  # news, social, forum
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'platform_name': self.platform_name,
            'platform_url': self.platform_url,
            'source_type': self.source_type,
            'is_active': self.is_active
        }


class MonitoredKeyword(db.Model):
    """关注关键词表"""
    __tablename__ = 'monitored_keywords'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    keyword = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='general')  # general, tech, finance, social, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'keyword': self.keyword,
            'category': self.category,
            'is_active': self.is_active
        }


class Event(db.Model):
    """舆情事件表"""
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    summary = db.Column(db.Text, default='')
    event_time = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(200), default='')
    cause = db.Column(db.Text, default='')
    involved = db.Column(db.Text, default='')  # 涉事人物/机构
    heat_index = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50), default='social')  # social, tech, finance, health, education
    lifecycle_stage = db.Column(db.String(30), default='潜伏期')  # 潜伏期/成长期/高潮期/衰退期
    risk_level = db.Column(db.String(10), default='低')  # 低/中/高
    report_count = db.Column(db.Integer, default=0)
    positive_ratio = db.Column(db.Float, default=0.0)
    negative_ratio = db.Column(db.Float, default=0.0)
    neutral_ratio = db.Column(db.Float, default=0.0)
    source_trace = db.Column(db.Text, default='')  # JSON: 溯源信息
    fake_news_score = db.Column(db.Float, default=0.0)  # 虚假概率
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    reports = db.relationship('EventReport', backref='event', lazy='dynamic',
                              cascade='all, delete-orphan')
    keywords = db.relationship('EventKeyword', backref='event', lazy='dynamic',
                               cascade='all, delete-orphan')
    trends = db.relationship('EventTrend', backref='event', lazy='dynamic',
                             cascade='all, delete-orphan', order_by='EventTrend.date')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'event_time': self.event_time.isoformat() if self.event_time else '',
            'location': self.location,
            'cause': self.cause,
            'involved': self.involved,
            'heat_index': round(self.heat_index, 2),
            'category': self.category,
            'lifecycle_stage': self.lifecycle_stage,
            'risk_level': self.risk_level,
            'report_count': self.report_count,
            'positive_ratio': round(self.positive_ratio, 2),
            'negative_ratio': round(self.negative_ratio, 2),
            'neutral_ratio': round(self.neutral_ratio, 2),
            'fake_news_score': round(self.fake_news_score, 2),
            'created_at': self.created_at.isoformat() if self.created_at else ''
        }

    def to_detail_dict(self):
        d = self.to_dict()
        d['reports'] = [r.to_dict() for r in self.reports.limit(100).all()]
        d['keywords'] = [k.to_dict() for k in self.keywords.order_by(
            EventKeyword.weight.desc()).limit(50).all()]
        d['trends'] = [t.to_dict() for t in self.trends.all()]
        d['platform_distribution'] = self._get_platform_distribution()
        d['source_trace'] = self.source_trace
        return d

    def _get_platform_distribution(self):
        """获取平台分布统计"""
        from sqlalchemy import func
        result = db.session.query(
            EventReport.platform,
            func.count(EventReport.id)
        ).filter(EventReport.event_id == self.id).group_by(EventReport.platform).all()
        return [{'platform': r[0], 'count': r[1]} for r in result]

    def __repr__(self):
        return f'<Event {self.title}>'


class EventReport(db.Model):
    """事件报道表"""
    __tablename__ = 'event_reports'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default='')
    source_url = db.Column(db.String(500), default='')
    platform = db.Column(db.String(50), default='未知')  # 来源平台
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(100), default='')
    sentiment_score = db.Column(db.Float, default=0.0)  # -1到1, 负→正
    is_original = db.Column(db.Boolean, default=False)  # 是否首发
    is_key_node = db.Column(db.Boolean, default=False)  # 是否关键传播节点
    node_type = db.Column(db.String(50), default='')  # 节点类型: origin/vip_repost/official
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'title': self.title,
            'content': self.content[:200] if self.content else '',
            'source_url': self.source_url,
            'platform': self.platform,
            'publish_time': self.publish_time.isoformat() if self.publish_time else '',
            'author': self.author,
            'sentiment_score': round(self.sentiment_score, 2),
            'is_original': self.is_original,
            'is_key_node': self.is_key_node,
            'node_type': self.node_type
        }


class EventKeyword(db.Model):
    """事件关键词表"""
    __tablename__ = 'event_keywords'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    keyword = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Float, default=0.0)  # TF-IDF权重

    def to_dict(self):
        return {
            'keyword': self.keyword,
            'weight': round(self.weight, 4)
        }


class EventTrend(db.Model):
    """事件趋势数据表"""
    __tablename__ = 'event_trends'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    report_count = db.Column(db.Integer, default=0)
    key_node = db.Column(db.String(200), default='')  # 该日关键节点描述
    positive_count = db.Column(db.Integer, default=0)
    negative_count = db.Column(db.Integer, default=0)
    neutral_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'date': self.date.isoformat() if self.date else '',
            'report_count': self.report_count,
            'key_node': self.key_node,
            'positive_count': self.positive_count,
            'negative_count': self.negative_count,
            'neutral_count': self.neutral_count
        }


class QAHistory(db.Model):
    """问答记录表"""
    __tablename__ = 'qa_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'question': self.question,
            'answer': self.answer,
            'created_at': self.created_at.isoformat() if self.created_at else ''
        }
